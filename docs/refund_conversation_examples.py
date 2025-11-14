"""
Example conversation flow demonstrating the complete refund logic.
This shows how the LLM uses the refund tools in a real conversation.
"""

# Example 1: Successful Refund - Personal Care Item
print("""
========================================
EXAMPLE 1: SUCCESSFUL REFUND
Product: Personal Care (Eligible)
========================================

Customer: "Hi, I want a refund for order ORD000032"

LLM Analysis:
  - NLU: intent="request_refund" (96%), sentiment="neutral"
  - Extracted Order ID: ORD000032
  
LLM Action 1: call check_refund_eligibility("ORD000032")
Response: {
  "eligible": true,
  "order_id": "ORD000032",
  "product_category": "Personal Care",
  "order_value": 1651,
  "shipping_fee": 82.55,
  "refund_amount": 1568.45,
  "message": "Your order for Personal Care (₹1,651) is eligible for refund..."
}

Bot: "I found your order for Personal Care items worth ₹1,651. After 
      deducting the 5% shipping fee (₹82.55), you will receive ₹1,568.45 
      as a refund. Would you like me to proceed with the refund?"

Customer: "Yes, please proceed"

LLM Action 2: call process_refund("ORD000032", 1568.45, "Customer request")
Response: {
  "status": "success",
  "transaction_id": "RFND_20251114123456_ORD000032",
  "order_id": "ORD000032",
  "amount_refunded": 1568.45,
  "message": "Refund processed successfully! ₹1,568.45 will be credited..."
}

Bot: "✅ Refund processed successfully! ₹1,568.45 will be credited to your 
      account within 5-7 business days. Your transaction ID is 
      RFND_20251114123456_ORD000032. Is there anything else I can help you with?"

DATABASE UPDATE:
  Order ORD000032 now has:
    - Refund Requested: "Processed"
    - Refund Amount: 1568.45
    - Refund Reason: "Customer request"
    - Refund Date: "2025-11-14T12:34:56.789Z"
""")

# Example 2: Rejected Refund - Food & Beverage
print("""
========================================
EXAMPLE 2: REJECTED REFUND
Product: Beverages (Not Eligible)
========================================

Customer: "I want my money back for ORD000003, the drinks were warm!"

LLM Analysis:
  - NLU: intent="request_refund" (98%), sentiment="negative" (85%)
  - Extracted Order ID: ORD000003
  
LLM Action: call check_refund_eligibility("ORD000003")
Response: {
  "eligible": false,
  "order_id": "ORD000003",
  "product_category": "Beverages",
  "order_value": 599,
  "reason": "Food & Beverage items (Beverages) cannot be refunded due to health and safety regulations.",
  "message": "I'm sorry, but we cannot process refunds for Beverages items..."
}

Bot: "I understand your frustration with the warm drinks. Unfortunately, 
      we cannot process refunds for Beverages items due to health and 
      safety regulations. However, I'd like to help resolve this issue. 
      Would you like me to connect you with a customer support agent who 
      can discuss alternative solutions, such as a replacement order or 
      store credit?"

Customer: "Yes, connect me to an agent"

LLM Action: call request_human_intervention(
  reason="Customer dissatisfied with warm beverages, refund not possible due to F&B policy",
  last_message="Yes, connect me to an agent",
  priority="medium"
)

Bot: "I've escalated this to our customer support team. A human agent will 
      reach out to you shortly to discuss the best solution for your situation. 
      Your case ID has been created with medium priority."
""")

# Example 3: Refund with Clarification
print("""
========================================
EXAMPLE 3: REFUND WITH CLARIFICATION
Missing Order ID Initially
========================================

Customer: "I want a refund, the product never arrived!"

LLM Analysis:
  - NLU: intent="request_refund" (92%), sentiment="negative" (88%)
  - No Order ID extracted
  
Bot: "I'm sorry to hear your order hasn't arrived. I'll be happy to help 
      you with a refund. Could you please provide your Order ID? It should 
      look like 'ORD000001' and can be found in your order confirmation."

Customer: "It's ORD000045"

LLM Action 1: call check_refund_eligibility("ORD000045")
Response: {
  "eligible": true,
  "order_id": "ORD000045",
  "product_category": "Personal Care",
  "order_value": 323,
  "shipping_fee": 16.15,
  "refund_amount": 306.85,
  "message": "Your order for Personal Care (₹323) is eligible for refund..."
}

Bot: "I've found your order for Personal Care items worth ₹323. I'm sorry 
      it didn't arrive. After deducting the 5% shipping fee (₹16.15), you 
      will receive ₹306.85 as a refund. Shall I process this refund for you?"

Customer: "Yes"

LLM Action 2: call process_refund("ORD000045", 306.85, "Order not delivered - customer request")
Response: {
  "status": "success",
  "transaction_id": "RFND_20251114124501_ORD000045",
  "amount_refunded": 306.85
}

Bot: "✅ Refund processed! ₹306.85 will be credited to your account within 
      5-7 business days. Transaction ID: RFND_20251114124501_ORD000045. 
      I apologize for the delivery issue."
""")

# Example 4: Duplicate Refund Attempt
print("""
========================================
EXAMPLE 4: DUPLICATE REFUND ATTEMPT
Order Already Refunded
========================================

Customer: "I want a refund for ORD000032"

LLM Action 1: call check_refund_eligibility("ORD000032")
Response: {
  "eligible": true,
  "order_id": "ORD000032",
  "product_category": "Personal Care",
  "order_value": 1651,
  "shipping_fee": 82.55,
  "refund_amount": 1568.45
}

Bot: "I can help you with that. After the 5% shipping fee, you'll receive 
      ₹1,568.45. Would you like to proceed?"

Customer: "Yes"

LLM Action 2: call process_refund("ORD000032", 1568.45, "Customer request")
Response: {
  "status": "failed",
  "error": "This order has already been refunded."
}

Bot: "I've checked your order and found that it has already been refunded. 
      The refund for ₹1,568.45 was processed earlier and should be reflected 
      in your account within 5-7 business days from the refund date. 
      Is there anything else I can help you with?"
""")

# Example 5: Multiple Orders - Topic Switch
print("""
========================================
EXAMPLE 5: MULTIPLE ORDERS
Topic Switch During Conversation
========================================

Customer: "I need help with order ORD000001"

Bot: "I'd be happy to help! What do you need assistance with for order 
      ORD000001?"

Customer: "Actually, forget that one. I want a refund for ORD000010 instead"

LLM Analysis:
  - Topic switch detected
  - New NLU analysis needed
  
LLM Action 1: call smart_triage_nlu("I want a refund for ORD000010")
Response: {
  "intent": "request_refund",
  "intent_confidence": 0.97,
  "sentiment": "neutral"
}

LLM Action 2: call check_refund_eligibility("ORD000010")
Response: {
  "eligible": false,
  "order_id": "ORD000010",
  "product_category": "Grocery",
  "order_value": 1279,
  "reason": "Food & Beverage items (Grocery) cannot be refunded..."
}

Bot: "I understand you'd like a refund for order ORD000010. Unfortunately, 
      we cannot process refunds for Grocery items due to health and safety 
      policies. Is there another way I can assist you with this order?"
""")

print("""
========================================
KEY TAKEAWAYS
========================================

1. ✅ LLM ALWAYS calls check_refund_eligibility FIRST
2. ✅ Food & Beverage items are automatically rejected
3. ✅ 5% shipping fee is automatically calculated
4. ✅ Customer confirmation is ALWAYS required before processing
5. ✅ Database is updated only after successful refund
6. ✅ Duplicate refunds are prevented
7. ✅ Transaction IDs are generated for tracking
8. ✅ Empathetic responses for negative sentiment

The refund logic seamlessly integrates with:
- NLU analysis (intent and sentiment)
- Order database queries
- Human escalation when needed
- Chat history and context management
""")
