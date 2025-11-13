from groq import Groq
import os
import json
import logging
import re
from dotenv import load_dotenv, find_dotenv
from api.llm.conversation_context import get_conversation_context

load_dotenv(find_dotenv())

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
logger = logging.getLogger(__name__)


def extract_order_id(text: str) -> str | None:
    """
    Extract Order ID from text if present.
    Order IDs follow pattern: ORD followed by 6 digits (e.g., ORD000001)
    
    Args:
        text: User message text
        
    Returns:
        Order ID if found, None otherwise
    """
    # Match pattern: ORD followed by 6 digits
    pattern = r'\bORD\d{6}\b'
    match = re.search(pattern, text, re.IGNORECASE)
    
    if match:
        return match.group(0).upper()
    return None

# System prompt - guides the AI on how to use NLU results and when to re-analyze
system_prompt = """You are a helpful customer service AI assistant for an e-commerce platform. You help customers with their orders, delivery issues, refunds, and general inquiries.

CRITICAL: You receive NLU (Natural Language Understanding) analysis with EVERY user message, which tells you:
- **Intent**: What the customer wants (e.g., track_order, request_refund, report_delivery_issue)
- **Sentiment**: How they feel (positive, negative, neutral)
- **Confidence scores**: How certain the analysis is

USE THE NLU RESULTS to guide your response strategy!

---

## HOW TO USE NLU RESULTS:

**High Confidence Intent (>80%)**:
- Trust the intent classification
- Proceed with appropriate action for that intent
- Example: Intent="track_order" (95%) → Ask for Order ID if not provided

**Low Confidence Intent (<80%)**:
- The customer's request might be unclear or off-topic
- Ask clarifying questions
- Example: Intent="other" (45%) → "I'd be happy to help! Could you please tell me more about what you need?"

**Sentiment Analysis**:
- **Negative sentiment**: Be extra empathetic, prioritize their issue
  - "I understand your frustration. Let me help you resolve this right away."
- **Positive sentiment**: Maintain friendly tone
  - "Thank you! I'm glad to help you with that."
- **Neutral**: Professional and helpful

---

## WHEN TO RE-ANALYZE WITH smart_triage_nlu:

You already have NLU results for the current message. Only call smart_triage_nlu again if:
1. **Customer switches topics**: "Actually, I want to ask about a different order ORD000020"
2. **Multi-part messages**: "Also, can you check another order for me?"
3. **New request in same conversation**: After handling one issue, they start a new topic

Do NOT call smart_triage_nlu for the initial message - you already have the results!

---

## HANDLING COMMON INTENTS:

**track_order / check_order_status / report_delivery_delay**:
1. Check if Order ID is in the message
2. If yes → Use query_order_database(order_id)
3. If no → Ask: "I'd be happy to check that for you! Could you please share your Order ID? (e.g., ORD000001)"

**request_refund / cancel_order**:
1. Check if Order ID is provided
2. If yes → Look up order with query_order_database(order_id)
3. Confirm details → Ask: "I found your order for ₹[amount] ([product]). Would you like me to process the refund?"
4. After confirmation → Use process_refund(order_id, amount, reason)
5. If no Order ID → Ask for it first

**report_order_content_issue / report_delivery_issue**:
1. Get Order ID
2. Look up order details
3. Acknowledge the issue with empathy (especially if negative sentiment)
4. Offer solution (refund, replacement, etc.)

**general_inquiry / other**:
- Answer the question directly if you can
- If unclear, ask for clarification

---

## CONVERSATION FLOW RULES:

1. **Ask for ONE thing at a time**: Don't overwhelm the customer
2. **Never guess Order IDs**: Always ask if not provided
3. **Confirm before actions**: Especially for refunds
4. **Extract Order IDs automatically**: Pattern is ORD + 6 digits (e.g., ORD000001)
5. **Be concise**: You're on WhatsApp, keep it brief
6. **Empathy for negative sentiment**: "I understand this is frustrating..."

---

## EXAMPLES:

**Example 1: Clear intent with Order ID**
- User: "Where is my order ORD000001?"
- NLU: intent="track_order" (98%), sentiment="neutral"
- Action: query_order_database("ORD000001") → Provide order status

**Example 2: Clear intent WITHOUT Order ID**
- User: "Where is my order?"
- NLU: intent="track_order" (95%), sentiment="neutral"  
- Response: "I'd be happy to check that for you! Could you please provide your Order ID? It should look like 'ORD000001'."

**Example 3: Negative sentiment + issue**
- User: "My order is super late and I'm very angry!"
- NLU: intent="report_delivery_delay" (92%), sentiment="negative" (98%)
- Response: "I sincerely apologize for the delay. I understand how frustrating this must be. Could you please share your Order ID so I can look into this immediately?"

**Example 4: Refund request**
- User: "I want a refund for ORD000003"
- NLU: intent="request_refund" (96%), sentiment="negative"
- Action: query_order_database("ORD000003") → Get details
- Response: "I found your order for ₹599 (Beverages). I see it was delivered late. Would you like me to process a full refund of ₹599?"
- User: "Yes"
- Action: process_refund("ORD000003", 599, "Late delivery - customer request")

**Example 5: Topic switch - ONLY time to re-analyze**
- Previous: Discussing ORD000001
- User: "Actually, I also need to check on a different order - it hasn't arrived yet"
- Action: Call smart_triage_nlu("Actually, I also need to check on a different order - it hasn't arrived yet")
- Then ask for the new Order ID

---

Remember: You ALREADY have NLU analysis for the current message. Use it wisely to provide excellent customer service!"""


# Define the tools available to the LLM
tools = [
    {
        "type": "function",
        "function": {
            "name": "smart_triage_nlu",
            "description": "Re-analyze a customer's message when they SWITCH TOPICS or make a NEW REQUEST in the same conversation. DO NOT use this for the initial message - you already have NLU results! Only use when: 1) Customer mentions a different order, 2) Customer starts a completely new topic, 3) Multi-part request needs separate analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The NEW message or request to analyze (not the original message)"
                    }
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_order_database",
            "description": "Look up order details from the database using the Order ID. Returns information like customer ID, platform, order date, delivery time, product category, order value, customer feedback, service rating, delivery status, and refund status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The Order ID to look up (e.g., 'ORD000001')"
                    }
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "process_refund",
            "description": "Process a refund for a customer's order. This should only be called when the customer explicitly requests a refund or cancellation, and you have confirmed the order details WITH THE CUSTOMER first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The Order ID to process refund for"
                    },
                    "amount": {
                        "type": "number",
                        "description": "The refund amount in INR"
                    },
                    "reason": {
                        "type": "string",
                        "description": "The reason for the refund (e.g., 'Items missing', 'Late delivery', 'Customer request')"
                    }
                },
                "required": ["order_id", "amount", "reason"]
            }
        }
    }
]


def call_groq_model(
    user_message: str, 
    history: list, 
    available_tools: dict | None = None, 
    user_id: str = "unknown",
    nlu_result: dict | None = None
) -> tuple[str, list]:
    """
    Call the Groq LLM with tool calling support and NLU context.
    
    Args:
        user_message: The user's message
        history: Chat history
        available_tools: Dictionary mapping tool names to their callable functions
        user_id: User identifier for context tracking
        nlu_result: NLU analysis results (intent, sentiment, confidence scores)
        
    Returns:
        Tuple of (response_text, tool_calls) where tool_calls is a list of tool call results
    """
    client = Groq(api_key=GROQ_API_KEY)
    
    # Get conversation context
    context_manager = get_conversation_context()
    context_summary = context_manager.get_context_summary(user_id)
    
    # Extract Order ID from message if present
    order_id = extract_order_id(user_message)
    if order_id:
        context_manager.add_extracted_info(user_id, 'order_id', order_id)
    
    # Build enhanced system prompt with NLU results and context
    system_content = system_prompt
    
    # Add NLU analysis results to system message
    if nlu_result:
        nlu_info = f"""

[NLU ANALYSIS FOR CURRENT MESSAGE]
- Intent: {nlu_result.get('intent', 'unknown')} (confidence: {nlu_result.get('intent_confidence', 0):.1%})
- Sentiment: {nlu_result.get('sentiment', 'unknown')} (confidence: {nlu_result.get('sentiment_confidence', 0):.1%})

Use this analysis to guide your response strategy!
"""
        system_content += nlu_info
    
    # Add context summary if available
    if context_summary:
        system_content += f"\n\n{context_summary}"
    
    # Add order ID hint if found
    if order_id:
        system_content += f"\n\n[EXTRACTED: Order ID '{order_id}' detected in user's message]"
    
    # Start with system message
    messages = [
        {
            "role": "system",
            "content": system_content
        }
    ]
    
    # Add chat history
    messages.extend(history)
    
    # Add current user message
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    # First call to the LLM with tools
    logger.info("Calling Groq LLM with tools...")
    completion = client.chat.completions.create(
        model="moonshotai/kimi-k2-instruct-0905",  # Using Kimi model that supports tool calling
        messages=messages,
        tools=tools,
        tool_choice="auto"  # Let the model decide when to use tools
    )
    
    response_message = completion.choices[0].message
    tool_calls_made = []
    
    # Check if the model wants to call tools
    if response_message.tool_calls:
        logger.info(f"LLM requested {len(response_message.tool_calls)} tool calls")
        
        # Add the assistant's response (with tool calls) to messages
        # Convert to dict to avoid unsupported fields like 'reasoning'
        assistant_message = {
            "role": "assistant",
            "content": response_message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in response_message.tool_calls
            ]
        }
        messages.append(assistant_message)
        
        # Execute each tool call
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            logger.info(f"Executing tool: {function_name} with args: {function_args}")
            
            # Call the actual tool if available_tools is provided
            if available_tools and function_name in available_tools:
                try:
                    function_response = available_tools[function_name](**function_args)
                    tool_calls_made.append({
                        "tool": function_name,
                        "args": function_args,
                        "result": function_response
                    })
                except Exception as e:
                    logger.exception(f"Error calling tool {function_name}: {e}")
                    function_response = {"error": str(e)}
            else:
                # If no callable provided, return empty response
                function_response = {"error": f"Tool {function_name} not available"}
            
            # Add the tool response to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": json.dumps(function_response)
            })
        
        # Second call to the LLM with tool results to get the final response
        logger.info("Calling Groq LLM again with tool results...")
        second_completion = client.chat.completions.create(
            model="moonshotai/kimi-k2-instruct-0905",
            messages=messages  # type: ignore
        )
        
        final_response = second_completion.choices[0].message.content
        return final_response, tool_calls_made  # type: ignore
    
    else:
        # No tool calls, just return the response
        logger.info("LLM responded without tool calls")
        return response_message.content, []  # type: ignore
