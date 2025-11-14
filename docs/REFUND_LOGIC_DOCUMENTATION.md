# Refund Logic Implementation

## Overview

This document explains the complete refund logic system implemented for the WhatsApp e-commerce customer service chatbot. The system integrates with the LLM to intelligently handle refund requests while enforcing business rules.

## Business Rules

### 1. **Product Category Restrictions**
- **Food & Beverage items CANNOT be refunded** due to health and safety regulations
- Food & Beverage categories include:
  - Beverages
  - Snacks
  - Dairy
  - Fruits & Vegetables
  - Grocery

- **Other categories CAN be refunded:**
  - Personal Care
  - Any other non-food categories

### 2. **Refund Calculation**
- A **5% shipping fee** is deducted from the order value
- Formula: `Refund Amount = Order Value - (Order Value × 0.05)`
- Example: ₹1,000 order → ₹50 shipping fee → ₹950 refund

### 3. **Refund Processing**
- Orders can only be refunded once
- Once refunded, the order status is updated in the database
- Duplicate refund attempts are rejected

## Architecture

### Components

1. **MCP Server Tools** (`api/mcp_server/mcp_server.py`)
   - `check_refund_eligibility(order_id)`: Checks if order can be refunded and calculates amount
   - `process_refund(order_id, amount, reason)`: Processes the refund and updates database

2. **MCP Client Wrappers** (`api/mcp_client/client.py`)
   - `check_refund_eligibility_sync(order_id)`: Synchronous wrapper for eligibility check
   - `process_refund_sync(order_id, amount, reason)`: Synchronous wrapper for processing

3. **LLM Integration** (`api/llm/groq_model.py`)
   - System prompt includes detailed refund workflow instructions
   - Tools available to LLM for intelligent refund handling

4. **Functions Layer** (`api/functions.py`)
   - Integrates MCP client tools into the conversation flow
   - Available in `generate_response()` function

## Workflow

### Complete Refund Process (3 Steps)

```
Customer: "I want a refund for ORD000001"
    ↓
[STEP 1] LLM calls check_refund_eligibility("ORD000001")
    ↓
    ├─ If ELIGIBLE (e.g., Personal Care):
    │     Returns: {
    │       "eligible": true,
    │       "order_value": 1651,
    │       "shipping_fee": 82.55,
    │       "refund_amount": 1568.45,
    │       "message": "Your order for Personal Care (₹1,651)..."
    │     }
    │     ↓
    │  [STEP 2] LLM presents refund amount and asks for confirmation
    │     LLM: "You will receive ₹1,568.45. Would you like to proceed?"
    │     Customer: "Yes"
    │     ↓
    │  [STEP 3] LLM calls process_refund("ORD000001", 1568.45, "Customer request")
    │     ↓
    │     Database updated with:
    │     - Refund Requested: "Processed"
    │     - Refund Amount: 1568.45
    │     - Refund Reason: "Customer request"
    │     - Refund Date: timestamp
    │     ↓
    │     Returns: {
    │       "status": "success",
    │       "transaction_id": "RFND_20251114123456_ORD000001",
    │       "amount_refunded": 1568.45,
    │       "message": "Refund processed successfully! ₹1,568.45..."
    │     }
    │
    └─ If NOT ELIGIBLE (e.g., Beverages):
          Returns: {
            "eligible": false,
            "reason": "Food & Beverage items (Beverages) cannot be refunded...",
            "message": "I'm sorry, but we cannot process refunds for..."
          }
          ↓
          LLM: Politely declines and offers alternative assistance
```

## Tool Specifications

### `check_refund_eligibility`

**Purpose:** Check if an order is eligible for refund and calculate refund amount

**Input:**
```json
{
  "order_id": "ORD000001"
}
```

**Output (Eligible):**
```json
{
  "eligible": true,
  "order_id": "ORD000001",
  "product_category": "Personal Care",
  "order_value": 1651,
  "shipping_fee": 82.55,
  "refund_amount": 1568.45,
  "message": "Your order for Personal Care (₹1,651) is eligible for refund..."
}
```

**Output (Not Eligible - Food & Beverage):**
```json
{
  "eligible": false,
  "order_id": "ORD000003",
  "product_category": "Beverages",
  "order_value": 599,
  "reason": "Food & Beverage items (Beverages) cannot be refunded due to health and safety regulations.",
  "message": "I'm sorry, but we cannot process refunds for Beverages items..."
}
```

**Output (Order Not Found):**
```json
{
  "eligible": false,
  "error": "Order ID not found."
}
```

### `process_refund`

**Purpose:** Process the refund and update database

**Input:**
```json
{
  "order_id": "ORD000001",
  "amount": 1568.45,
  "reason": "Customer request"
}
```

**Output (Success):**
```json
{
  "status": "success",
  "transaction_id": "RFND_20251114123456_ORD000001",
  "order_id": "ORD000001",
  "amount_refunded": 1568.45,
  "message": "Refund processed successfully! ₹1,568.45 will be credited to your account within 5-7 business days. Transaction ID: RFND_20251114123456_ORD000001"
}
```

**Output (Already Refunded):**
```json
{
  "status": "failed",
  "error": "This order has already been refunded."
}
```

**Output (Order Not Found):**
```json
{
  "status": "failed",
  "error": "Order ID not found."
}
```

## Database Schema

### Order Collection (`order_details`)

**Fields added/updated during refund:**
- `Refund Requested`: "No" → "Processed"
- `Refund Amount`: (float) Amount refunded
- `Refund Reason`: (string) Reason provided
- `Refund Date`: (ISO timestamp) When refund was processed

**Example:**
```json
{
  "Order ID": "ORD000001",
  "Product Category": "Personal Care",
  "Order Value (INR)": 1651,
  "Refund Requested": "Processed",
  "Refund Amount": 1568.45,
  "Refund Reason": "Customer request",
  "Refund Date": "2025-11-14T12:34:56.789Z"
}
```

## LLM Integration

### System Prompt Instructions

The LLM is trained to:

1. **Always use the 3-step workflow**
2. **Never bypass eligibility check** - must call `check_refund_eligibility` first
3. **Never manually calculate refund** - use the amount from eligibility check
4. **Always confirm with customer** before processing
5. **Handle rejections politely** for Food & Beverage items

### Example Conversations

**Example 1: Successful Refund (Personal Care)**
```
User: "I want a refund for ORD000032"
Bot: [Calls check_refund_eligibility("ORD000032")]
Bot: "I found your order for Personal Care (₹1,651). After deducting 
      the 5% shipping fee (₹82.55), you will receive ₹1,568.45 as refund. 
      Would you like to proceed?"
User: "Yes please"
Bot: [Calls process_refund("ORD000032", 1568.45, "Customer request")]
Bot: "Refund processed successfully! ₹1,568.45 will be credited to your 
      account within 5-7 business days. Transaction ID: RFND_20251114123456_ORD000032"
```

**Example 2: Rejected Refund (Food & Beverage)**
```
User: "I want a refund for ORD000003"
Bot: [Calls check_refund_eligibility("ORD000003")]
Bot: "I'm sorry, but we cannot process refunds for Beverages items due 
      to health and safety policies. Is there another way I can help you 
      with this order?"
```

**Example 3: Duplicate Refund Attempt**
```
User: "Refund ORD000032 again"
Bot: [Calls check_refund_eligibility("ORD000032") - might still return eligible]
Bot: "Would you like to proceed with the refund?"
User: "Yes"
Bot: [Calls process_refund("ORD000032", ...)]
Bot: "I'm sorry, but this order has already been refunded. The previous 
      refund was processed on 2025-11-14. Is there anything else I can help with?"
```

## Testing

### Test Script: `scripts/test_refund_logic.py`

Run the test suite:
```bash
python scripts/test_refund_logic.py
```

**Tests included:**
1. **Eligibility Check** - Tests various product categories
2. **Complete Workflow** - End-to-end refund processing
3. **Food & Beverage Rejection** - Verifies F&B items are rejected
4. **Duplicate Prevention** - Ensures orders can't be refunded twice

### Manual Testing

1. Start the MCP server
2. Use the simulate script or WhatsApp interface
3. Test refund requests for different product categories
4. Verify database updates

## Error Handling

### Common Errors and Solutions

1. **Order Not Found**
   - Error: "Order ID not found."
   - Solution: Verify order ID format (ORD + 6 digits)

2. **Already Refunded**
   - Error: "This order has already been refunded."
   - Solution: Check database, inform customer refund was already processed

3. **Database Update Failed**
   - Error: "Failed to update database."
   - Solution: Check MongoDB connection and permissions

4. **Food & Beverage Item**
   - Not an error - expected behavior
   - LLM should politely decline and offer alternatives

## Security Considerations

1. **Authentication**: Verify user owns the order (through user_id in chat history)
2. **Authorization**: Only process refunds for confirmed orders
3. **Audit Trail**: All refunds logged with timestamp, amount, and reason
4. **Idempotency**: Prevent duplicate refunds through database checks

## Future Enhancements

1. **Partial Refunds**: Support refunding specific items from multi-item orders
2. **Refund Reasons**: Categorize reasons for analytics
3. **Approval Workflow**: Require manager approval for high-value refunds
4. **Payment Gateway Integration**: Actually process refunds through payment APIs
5. **Customer Notifications**: Send email/SMS confirmation of refunds
6. **Refund History**: Show customer their refund history

## Maintenance

### Updating Business Rules

To modify refund rules, update these files:

1. **Category List**: `api/mcp_server/mcp_server.py` - `food_beverage_categories`
2. **Shipping Fee**: `api/mcp_server/mcp_server.py` - `shipping_fee_percent`
3. **System Prompt**: `api/llm/groq_model.py` - `system_prompt`

### Monitoring

Monitor these metrics:
- Refund request volume by category
- Acceptance vs rejection rate
- Average refund amount
- Refund processing time
- Customer satisfaction after refunds

## Support

For issues or questions:
1. Check the test script output
2. Review MCP server logs (stderr)
3. Verify MongoDB connection and data
4. Check LLM tool calling logs in functions.py
