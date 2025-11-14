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

## WHEN TO ESCALATE TO HUMAN AGENT (request_human_intervention):

Use request_human_intervention when:
1. **Customer explicitly asks**: "I want to speak to a human", "Can I talk to someone?", "I need a real person"
2. **Very negative sentiment** (>90% confidence) with complex issues: Customer is extremely frustrated and issue requires careful handling
3. **Cannot resolve with available tools**: Issue is outside your capability (e.g., account security, legal matters, custom requests)
4. **Complex disputes**: Refund disputes, damaged items requiring investigation, missing orders with delivery confirmation
5. **Repeated failures**: You've tried to help but couldn't resolve after 2-3 attempts
6. **Manual investigation needed**: Issues requiring access to systems you don't have

When escalating, set priority:
- **high**: Very frustrated customers (negative sentiment >90%), urgent issues, repeated failures
- **medium**: Standard complex issues, explicit human requests
- **low**: General inquiries that need human expertise but aren't urgent

After calling request_human_intervention:
- Inform the customer: "I've escalated this to our support team. A human agent will reach out to you shortly to assist with [issue]. Is there anything else I can help with in the meantime?"
- Be empathetic and reassuring

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
5. If requires physical inspection/investigation → Escalate to human

**general_inquiry / other**:
- Answer the question directly if you can
- If unclear, ask for clarification
- If outside your knowledge → Escalate to human

---

## CONVERSATION FLOW RULES:

1. **Ask for ONE thing at a time**: Don't overwhelm the customer
2. **Never guess Order IDs**: Always ask if not provided
3. **Confirm before actions**: Especially for refunds
4. **Extract Order IDs automatically**: Pattern is ORD + 6 digits (e.g., ORD000001)
5. **Be concise**: You're on WhatsApp, keep it brief
6. **Empathy for negative sentiment**: "I understand this is frustrating..."
7. **Escalate when necessary**: Don't struggle - get human help when needed. Always escalate to human agents when asked.

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

**Example 4: Refund request - COMPLETE WORKFLOW**
- User: "I want a refund for ORD000003"
- NLU: intent="request_refund" (96%), sentiment="negative"
- STEP 1: Check eligibility with check_refund_eligibility("ORD000003")
- If ELIGIBLE → Response: "I found your order for Personal Care (₹1,651). After deducting the 5% shipping fee (₹82.55), you will receive ₹1,568.45 as refund. Would you like to proceed?"
- If NOT ELIGIBLE (Food & Beverage) → Response: "I'm sorry, but we cannot process refunds for Beverages items due to health and safety policies. Is there another way I can help you with this order?"
- STEP 2: If customer confirms ("Yes", "OK", "Proceed") → process_refund("ORD000003", 1568.45, "Customer request")
- STEP 3: Provide confirmation with transaction ID

**Example 5: Escalation - Explicit request**
- User: "I need to speak with a human agent"
- Action: request_human_intervention(reason="Customer explicitly requested human agent", last_message="I need to speak with a human agent", priority="medium")
- Response: "I've escalated this to our support team. A human agent will reach out to you shortly. Is there anything else I can help with in the meantime?"

**Example 6: Escalation - Very frustrated customer**
- User: "This is absolutely unacceptable! I've been waiting for 2 weeks and no one has helped me!"
- Action: request_human_intervention(reason="Highly frustrated customer with prolonged unresolved issue", last_message="This is absolutely unacceptable! I've been waiting for 2 weeks and no one has helped me!", priority="high")
- Response: "I'm truly sorry for the frustration and inconvenience you've experienced. This is not acceptable. I've immediately escalated your case to our senior support team with high priority. A human agent will contact you within the next few hours to resolve this. Could you please share your Order ID so I can provide them with all the details?"

**Example 7: Topic switch - ONLY time to re-analyze**
- Previous: Discussing ORD000001
- User: "Actually, I also need to check on a different order - it hasn't arrived yet"
- Action: Call smart_triage_nlu("Actually, I also need to check on a different order - it hasn't arrived yet")
- Then ask for the new Order ID

---

## REFUND WORKFLOW - CRITICAL:

**ALWAYS follow this 3-step process for refunds:**

1. **Check Eligibility**: Call check_refund_eligibility(order_id)
   - This checks if the product category allows refunds
   - Automatically calculates refund amount (original price - 5% shipping fee)
   - Food & Beverage items (Beverages, Snacks, Dairy, Fruits & Vegetables, Grocery) CANNOT be refunded

2. **Confirm with Customer**: 
   - If ELIGIBLE: Present the refund amount and ask for confirmation
     - "Your order for [category] (₹[original]) is eligible for refund. After deducting the 5% shipping fee (₹[fee]), you will receive ₹[refund_amount]. Would you like to proceed?"
   - If NOT ELIGIBLE: Politely decline and offer alternative assistance
     - "I'm sorry, but we cannot process refunds for [category] items due to health and safety policies. Is there another way I can help you with this order?"

3. **Process Refund**: ONLY if customer confirms
   - Call process_refund(order_id, refund_amount, reason)
   - Provide transaction ID and timeline
   - "Refund processed successfully! ₹[amount] will be credited to your account within 5-7 business days. Transaction ID: [id]"

**NEVER:**
- Process refund without checking eligibility first
- Process refund for Food & Beverage items
- Calculate refund amount manually (use check_refund_eligibility)
- Process refund without customer confirmation

---

Remember: You ALREADY have NLU analysis for the current message. Use it wisely to provide excellent customer service! When in doubt or facing complex issues, don't hesitate to escalate to human agents."""


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
            "name": "check_refund_eligibility",
            "description": "STEP 1 of refund process: Check if an order is eligible for refund based on product category and calculate the refund amount. Food & Beverage items (Beverages, Snacks, Dairy, Fruits & Vegetables, Grocery) CANNOT be refunded. For eligible items, automatically calculates refund amount by subtracting 5% shipping fee from order value. ALWAYS call this BEFORE process_refund.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The Order ID to check for refund eligibility (e.g., 'ORD000001')"
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
            "description": "STEP 3 of refund process: Process a refund and update the database to mark the order as refunded. ONLY call this after: 1) check_refund_eligibility confirms eligibility, 2) Customer explicitly confirms they want to proceed. This updates the order status in the database and generates a transaction ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The Order ID to process refund for"
                    },
                    "amount": {
                        "type": "number",
                        "description": "The refund amount in INR (use the amount from check_refund_eligibility)"
                    },
                    "reason": {
                        "type": "string",
                        "description": "The reason for the refund (e.g., 'Items missing', 'Late delivery', 'Customer request', 'Damaged product')"
                    }
                },
                "required": ["order_id", "amount", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "request_human_intervention",
            "description": "Escalate the conversation to a human customer support agent when: 1) The request is too complex for automated handling, 2) Customer explicitly asks to speak with a human, 3) The issue requires manual investigation, 4) You cannot resolve the issue with available tools, 5) Customer is very frustrated (highly negative sentiment) and needs human attention. The user_id is automatically injected, you only need to provide reason, last_message, and priority.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Detailed reason for escalation (e.g., 'Complex refund dispute', 'Customer requests human agent', 'Issue outside automation scope')"
                    },
                    "last_message": {
                        "type": "string",
                        "description": "The customer's last message that triggered the escalation"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Priority level - 'high' for very frustrated customers or urgent issues, 'medium' for standard escalations, 'low' for general inquiries"
                    }
                },
                "required": ["reason", "last_message"]
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
