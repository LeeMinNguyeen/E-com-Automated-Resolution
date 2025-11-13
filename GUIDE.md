# Complete Guide - E-com Automated Resolution

## Table of Contents
1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [Testing](#testing)
4. [Conversational Flow](#conversational-flow)
5. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites
- Python 3.8+
- MongoDB Atlas account
- Groq API key
- WhatsApp Business API credentials

### Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Create `.env` file:**
```env
MONGO_URI=mongodb+srv://your-connection-string
GROQ_API_KEY=your_groq_api_key
VERIFY_TOKEN=your_whatsapp_verify_token
APP_ID=your_whatsapp_app_id
APP_SECRET=your_whatsapp_app_secret
ACCESS_TOKEN=your_whatsapp_access_token
PHONE_ID=your_whatsapp_phone_id
```

3. **Populate MongoDB database:**
```bash
python scripts/push_csv_to_mongo.py
```

4. **Test the integration:**
```bash
python scripts/test_mcp_integration.py
```

5. **Start the bot:**
```bash
python api/main.py
```

---

## Architecture

### System Overview

```
User → WhatsApp → Bot → LLM (with tools) → MCP Client → MCP Server
                                                            ↓
                                                    [NLU Model]
                                                    [MongoDB]
                                                    [Refund Service]
```

### Components

1. **WhatsApp Bot** (`api/main.py`)
   - Receives messages via pywa
   - Saves chat history to MongoDB
   - Sends responses back to user

2. **Response Generator** (`api/functions.py`)
   - Retrieves chat history
   - Calls LLM with tool support
   - Passes user_id for context tracking

3. **Groq LLM** (`api/llm/groq_model.py`)
   - Analyzes user messages
   - Decides which tools to call
   - Asks for missing information
   - Generates contextual responses

4. **MCP Client** (`api/mcp_client/client.py`)
   - Connects to MCP server
   - Executes tool calls
   - Returns results to LLM

5. **MCP Server** (`api/mcp_server/mcp_server.py`)
   - Hosts 3 tools: smart_triage_nlu, query_order_database, process_refund
   - Uses trained NLU model (DistilBERT)
   - Queries MongoDB for order data
   - Simulates refund processing

### Available Tools

#### 1. smart_triage_nlu
Classifies customer intent and sentiment.

**Input:** `{"text": "My order is late!"}`

**Output:**
```json
{
  "intent": "delivery_complaint",
  "intent_confidence": 0.9234,
  "sentiment": "negative",
  "sentiment_confidence": 0.8876
}
```

#### 2. query_order_database
Looks up order details from MongoDB.

**Input:** `{"order_id": "ORD000001"}`

**Output:**
```json
{
  "Order ID": "ORD000001",
  "Platform": "JioMart",
  "Product Category": "Fruits & Vegetables",
  "Order Value (INR)": 382,
  "Service Rating": 5
}
```

#### 3. process_refund
Processes a refund for an order.

**Input:**
```json
{
  "order_id": "ORD000003",
  "amount": 599,
  "reason": "Items missing"
}
```

**Output:**
```json
{
  "status": "success",
  "transaction_id": "RFND_20250105123045_ORD000003",
  "amount_refunded": 599
}
```

---

## Testing

### Test Scenarios

#### Scenario 1: User Doesn't Provide Order ID

**User:** "Where is my order?"

**Bot:** "I'd be happy to check that for you! Could you please share your Order ID? It should start with 'ORD' followed by numbers."

**User:** "ORD000001"

**Bot:** "I found your order! It was delivered in 30 minutes from JioMart. You ordered Fruits & Vegetables worth ₹382."

---

#### Scenario 2: User Wants Refund

**User:** "I want a refund"

**Bot:** "I can help you with that. May I have your Order ID so I can look up your order details?"

**User:** "ORD000003"

**Bot:** "I found your order for ₹599 (Beverages). I see items were missing. Would you like me to process a refund for the full amount?"

**User:** "Yes"

**Bot:** "Refund processed! Transaction ID: RFND_20250105123045_ORD000003. You'll receive ₹599 back within 5-7 business days."

---

#### Scenario 3: Complete Info Provided

**User:** "Check order ORD000001"

**Bot:** *Immediately queries database*
"I found your order! It was delivered in 30 minutes from JioMart for ₹382 (Fruits & Vegetables)."

---

### Test Commands

**WhatsApp Messages to Try:**

1. `"Where is my order?"` - Tests missing info handling
2. `"I want a refund"` - Tests refund flow
3. `"Check order ORD000001"` - Tests auto-detection
4. `"My delivery is late and I'm angry!"` - Tests sentiment analysis
5. `"I need help"` - Tests general inquiry

**Expected Logs:**
```
INFO:api.llm.groq_model:User 1234567890: added order_id = ORD000001
INFO:api.llm.groq_model:Calling Groq LLM with tools...
INFO:api.mcp_client.client:Calling tool 'query_order_database'
INFO:api.functions:Tools called: ['query_order_database']
```

---

## Conversational Flow

### How It Works

The bot uses several mechanisms to handle incomplete requests:

#### 1. Order ID Auto-Detection
```python
Pattern: r'\bORD\d{6}\b'
Examples: ORD000001, ORD123456
Case-insensitive: ord000001 → ORD000001
```

#### 2. Context Tracking
Remembers conversation state:
```python
{
    'waiting_for': 'order_id',
    'pending_action': 'refund',
    'last_bot_question': 'May I have your Order ID?',
    'extracted_info': {'order_id': 'ORD000001'}
}
```

#### 3. Enhanced System Prompt
The LLM is instructed to:
- **Always ask** for missing information politely
- **Never guess** or assume details
- **Confirm** before taking actions like refunds
- **Be conversational** and concise (WhatsApp format)

### Example Flows

**Missing Order ID Flow:**
```
User: "Where is my order?"
  ↓
Bot detects: Need Order ID for order lookup
  ↓
Bot asks: "Could you please share your Order ID?"
  ↓
User: "ORD000001"
  ↓
Bot extracts: ORD000001
  ↓
Bot calls: query_order_database("ORD000001")
  ↓
Bot responds: Shows order details
```

**Refund Confirmation Flow:**
```
User: "I want a refund for ORD000003"
  ↓
Bot extracts: ORD000003
  ↓
Bot calls: query_order_database("ORD000003")
  ↓
Bot sees: ₹599, items missing
  ↓
Bot asks: "Would you like me to process a refund for ₹599?"
  ↓
User: "Yes"
  ↓
Bot calls: process_refund("ORD000003", 599, "Customer request")
  ↓
Bot responds: "Refund processed! Transaction ID: ..."
```

---

## Troubleshooting

### Common Issues

#### Issue: MCP Server Won't Start
**Symptoms:** Error connecting to MCP server

**Solutions:**
1. Check model files exist in `model/` directory
2. Verify MongoDB connection: `MONGO_URI` in `.env`
3. Ensure PyTorch is installed correctly
4. Check Python version (3.8+)

---

#### Issue: Tools Not Being Called
**Symptoms:** Bot responds without using tools

**Solutions:**
1. Verify Groq API key is valid
2. Check Groq account has credits
3. Ensure using model: `llama-3.3-70b-versatile`
4. Check logs for LLM decisions

---

#### Issue: Order Not Found
**Symptoms:** "Order ID not found" error

**Solutions:**
1. Run: `python scripts/push_csv_to_mongo.py`
2. Verify MongoDB collection: `order_details`
3. Check Order ID format: `ORD######`
4. Confirm MongoDB connection string

---

#### Issue: Bot Not Asking for Missing Info
**Symptoms:** Bot fails instead of asking

**Solutions:**
1. Check system prompt is loaded correctly
2. Verify conversation_context.py is imported
3. Check user_id is passed to LLM call
4. Review logs for context tracking

---

### Debug Tips

**Enable detailed logging:**
```python
logging.basicConfig(level=logging.DEBUG)
```

**Check conversation context:**
```python
from api.llm.conversation_context import get_conversation_context
context = get_conversation_context()
print(context.get_context("user_id"))
```

**Test MCP tools directly:**
```python
from api.mcp_client.client import smart_triage_sync
result = smart_triage_sync("My order is late!")
print(result)
```

---

## Project Structure

```
E-com-Automated-Resolution/
├── api/
│   ├── main.py                          # WhatsApp bot
│   ├── functions.py                     # Response generation
│   ├── db/mongo.py                      # MongoDB
│   ├── llm/
│   │   ├── groq_model.py               # LLM with tools
│   │   └── conversation_context.py     # Context tracking
│   ├── model/multitask_distil_bert.py  # NLU model
│   ├── mcp_client/client.py            # MCP client
│   └── mcp_server/mcp_server.py        # MCP server
├── model/                               # Trained model files
├── data/                                # CSV datasets
├── scripts/
│   ├── test_mcp_integration.py         # Tests
│   └── push_csv_to_mongo.py            # DB setup
├── README.md                            # Overview
├── GUIDE.md                             # This file
└── requirements.txt                     # Dependencies
```

---

## Key Features Summary

✅ **Conversational AI** - Asks for missing information naturally
✅ **Smart NLU** - Classifies intent and sentiment with 90%+ accuracy
✅ **Real-time DB** - Queries MongoDB for live order data
✅ **Auto-detection** - Extracts Order IDs automatically
✅ **Context-aware** - Remembers conversation across messages
✅ **Safe operations** - Always confirms before refunds
✅ **WhatsApp native** - Integrated with WhatsApp Business API
✅ **Tool-calling LLM** - Intelligently uses tools when needed

---

## Next Steps

1. **Production deployment:**
   - Add rate limiting
   - Implement error recovery
   - Add logging to files
   - Setup monitoring

2. **Expand capabilities:**
   - Order tracking tool
   - Product search tool
   - FAQ knowledge base
   - Multi-language support

3. **Improve performance:**
   - Cache frequent queries
   - Optimize MCP connection
   - Fine-tune prompts

---

**For quick reference, see README.md**
**For issues, check the Troubleshooting section above**
