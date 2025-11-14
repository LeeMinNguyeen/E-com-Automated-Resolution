import logging
import requests
import os
from dotenv import load_dotenv, find_dotenv

from api.llm.groq_model import *
from api.db.mongo import *
from api.llm.conversation_context import get_conversation_context
from api.mcp_client.client import (
    smart_triage_sync,
    query_order_sync,
    check_refund_eligibility_sync,
    process_refund_sync,
    request_human_intervention_sync
)

# configure module logger
logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())

VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
PAGE_ACCESS_TOKEN = os.getenv('PAGE_ACCESS_TOKEN')
API_VERSION = os.getenv('API_VERSION', 'v24.0')
# PAGE_ID = os.getenv('FB_PAGE_ID') or os.getenv('PAGE_ID')

def _get_user_chat_history(user_id: str):
    """Retrieve chat history for a user from the database."""
    chat_history = get_chat_history(user_id)
    return chat_history

def save_message(user_id: str, from_role: str, to_role: str, text: str, timestamp: int):
    data = {
        "user_id": user_id,
        "from": from_role,
        "to": to_role,
        "text": text,
        "timestamp": timestamp
    }
    db = get_mongo_client()
    db, chat_collection = get_database() # type: ignore
    try:
        chat_collection.insert_one(data) # type: ignore
    except Exception as e:
        logger.exception("Failed to save message to MongoDB: %s", e)

    return True

def generate_response(user_id: str, message: str):
    """
    Generate a response using the LLM with MCP tool calling support.
    
    OPTIMIZED FLOW:
    1. Check if NLU analysis is needed (first message OR 24+ hours since last message)
    2. If needed, run NLU analysis; otherwise use cached result
    3. Pass message + NLU results to LLM
    4. LLM decides what to do based on intent
    5. LLM can call additional tools (query DB, process refund, re-analyze intent,...)
    6. Return the final response
    """
    try:
        # Get conversation context manager
        context_manager = get_conversation_context()
        
        # Update message timestamp
        context_manager.update_message_timestamp(user_id)
        
        # Get chat history
        chat_history = _get_user_chat_history(user_id)
        logger.info("Chat history for user %s: %d messages", user_id, len(chat_history))
        
        # STEP 1: Smart NLU Analysis - only run when needed
        if context_manager.should_run_nlu(user_id):
            logger.info("Running NLU analysis on user message (first message or 24h+ gap)...")
            nlu_result = smart_triage_sync(message)
            context_manager.update_nlu_result(user_id, nlu_result)
            logger.info(f"NLU Result - Intent: {nlu_result.get('intent')} ({nlu_result.get('intent_confidence', 0):.2%}), "
                       f"Sentiment: {nlu_result.get('sentiment')} ({nlu_result.get('sentiment_confidence', 0):.2%})")
        else:
            # Use cached NLU result
            nlu_result = context_manager.get_cached_nlu_result(user_id)
            if nlu_result:
                logger.info(f"Using cached NLU result - Intent: {nlu_result.get('intent')}, Sentiment: {nlu_result.get('sentiment')}")
            else:
                # Fallback: run NLU if cache is somehow empty
                logger.warning("Cache expected but empty, running NLU analysis...")
                nlu_result = smart_triage_sync(message)
                context_manager.update_nlu_result(user_id, nlu_result)
        
        # STEP 2: Define the available tools that the LLM can call
        # Note: LLM can still call smart_triage_nlu if user changes topic or new request
        
        # Create a wrapper for request_human_intervention that auto-injects user_id
        def request_human_intervention_wrapper(reason: str, last_message: str, priority: str = "medium"):
            """Wrapper that automatically injects the current user_id"""
            return request_human_intervention_sync(
                user_id=user_id,  # Auto-inject the actual user_id
                reason=reason,
                last_message=last_message,
                priority=priority
            )
        
        available_tools = {
            "smart_triage_nlu": smart_triage_sync,
            "query_order_database": query_order_sync,
            "check_refund_eligibility": check_refund_eligibility_sync,
            "process_refund": process_refund_sync,
            "request_human_intervention": request_human_intervention_wrapper  # Use wrapper
        }
        
        # STEP 3: Call the LLM with message, NLU results, and tools
        answer, tool_calls = call_groq_model(
            user_message=message,
            history=chat_history,
            available_tools=available_tools,
            user_id=user_id,
            nlu_result=nlu_result  # Pass NLU results to LLM
        )
        
        # STEP 4: If LLM called smart_triage_nlu (topic change), update cache
        if tool_calls:
            for tc in tool_calls:
                if tc['tool'] == 'smart_triage_nlu' and 'result' in tc:
                    # Update cached NLU result with new analysis
                    context_manager.update_nlu_result(user_id, tc['result'])
                    logger.info("Updated NLU cache due to topic change")
        
        # Log tool calls for debugging
        if tool_calls:
            logger.info(f"Tools called: {[tc['tool'] for tc in tool_calls]}")
            for tc in tool_calls:
                logger.info(f"  {tc['tool']}: {tc['result']}")
        
        return answer
        
    except Exception as e:
        logger.exception("Failed to generate response: %s", e)
        return "Sorry, I encountered an error processing your request. Please try again later."
