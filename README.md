# E-commerce Automated Resolution System

An intelligent WhatsApp chatbot for automated e-commerce customer support powered by AI. This system combines a fine-tuned DistilBERT model for natural language understanding with Groq's LLM for conversational AI, using the Model Context Protocol (MCP) for tool orchestration.

## 🌟 Overview

This project implements an end-to-end AI-powered customer service agent that handles e-commerce queries through WhatsApp. The system intelligently triages customer messages, queries order databases, processes refunds, and maintains conversational context - all while providing a natural, human-like interaction experience.

### Key Features

- 🤖 **Conversational AI**: Natural language interactions powered by Groq's Kimi-K2 LLM
- 🎯 **Smart NLU Triage**: Multi-task DistilBERT model for intent classification and sentiment analysis (90%+ accuracy)
- ⚡ **Optimized Resource Usage**: NLU runs only on first message or after 24h gap (cached otherwise)
- 💬 **WhatsApp Integration**: Native integration with WhatsApp Business API using PyWa
- 🔧 **MCP Tool Orchestration**: Model Context Protocol for seamless AI-tool integration
- 🗄️ **Real-time Database**: MongoDB for order data and chat history
- 🧠 **Context Awareness**: Maintains conversation context and tracks user information
- 💰 **Smart Refund Processing**: Intelligent refund handling with automatic order lookup and confirmation
- 🔍 **Auto Order ID Detection**: Automatic extraction of order IDs from messages (pattern: ORD000001)
- 📊 **Intent-Driven Responses**: LLM receives NLU intent/sentiment to make informed decisions
- 🚨 **Human Escalation**: Intelligent routing to support agents for complex issues
- 📈 **Real-time Dashboard**: Monitor chatbot performance, manage alerts, track metrics

## 📋 Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Components](#components)
- [Available Tools](#available-tools)
- [Customer Support Dashboard](#customer-support-dashboard)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐     ┌─────────────────┐
│   WhatsApp  │────▶│  FastAPI Bot │────▶│  Groq LLM       │
│   Business  │◀────│  (PyWa)      │◀────│  (w/ Tools)     │
└─────────────┘      └──────────────┘     └────────┬────────┘
                            │                      │
                            ▼                      ▼
                    ┌──────────────┐     ┌─────────────────┐
                    │   MongoDB    │────▶│ Streamlit       │
                    │  (Chat + DB) │     │ Dashboard       │
                    └──────────────┘     └─────────────────┘
                            ▲                      
                            │                      
                            ▼                      
                    ┌─────────────────┐
                    │   MCP Client    │
                    └────────┬────────┘
                             │
                             ▼
                   ┌─────────────────┐
                   │   MCP Server    │
                   │   - NLU Model   │
                   │   - Order DB    │
                   │   - Refunds     │
                   │   - Alerts      │
                   └─────────────────┘
```

### System Flow

1. **User sends message** via WhatsApp
2. **Bot receives message** and saves to MongoDB
3. **NLU Analysis** (smart caching):
   - Runs on first message
   - Runs if 24+ hours since last message
   - Otherwise uses cached result (optimized!)
4. **Response generator** retrieves chat history
5. **Groq LLM** (Kimi-K2 model) receives:
   - User message
   - NLU results (intent + sentiment)
   - Conversation context
   - Chat history
6. **MCP Client** executes tool calls as needed:
   - `smart_triage_nlu`: Re-analyzes if user switches topics
   - `query_order_database`: Fetches order details from MongoDB
   - `process_refund`: Handles refund processing
   - `request_human_intervention`: Escalates to human agents
7. **Bot sends response** back to user via WhatsApp
8. **Dashboard** monitors performance and displays alerts in real-time

## 📦 Prerequisites

- **Python 3.8+**
- **MongoDB Atlas Account** (or local MongoDB instance)
- **Groq API Key** ([Get one here](https://console.groq.com))
- **WhatsApp Business API Credentials**:
  - App ID
  - App Secret
  - Access Token
  - Phone Number ID
  - Verify Token
- **ngrok** (for local development webhooks)
- **CUDA-capable GPU** (optional, for faster inference)

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/LeeMinNguyeen/E-com-Automated-Resolution.git
cd E-com-Automated-Resolution
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
.venv\Scripts\activate  # On Windows
# source .venv/bin/activate  # On Linux/Mac
```

### 3. Install PyTorch with CUDA Support (Optional)

For GPU acceleration:

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

For CPU-only:

```bash
pip install torch torchvision torchaudio
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Setup MongoDB

1. Create a MongoDB Atlas cluster or use local MongoDB
2. Create a database (e.g., `ecommerce_support`)
3. Create collections:
   - `order_details`: For order information
   - `chats`: For conversation history
   - `human_intervention_alerts`: For escalation alerts

## ⚙️ Configuration

### 1. Create `.env` File

Create a `.env` file in the project root:

```env
# MongoDB Configuration
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/

# Groq API Configuration
GROQ_API_KEY=gsk_your_groq_api_key_here

# WhatsApp Business API Configuration
VERIFY_TOKEN=your_random_verify_token
APP_ID=your_whatsapp_app_id
APP_SECRET=your_whatsapp_app_secret
ACCESS_TOKEN=your_whatsapp_access_token
PHONE_ID=your_whatsapp_phone_number_id
```

### 2. Populate MongoDB with Sample Data

```bash
python scripts/push_csv_to_mongo.py
```

This script loads the e-commerce analytics data from `data/Ecommerce_Delivery_Analytics_New.csv` into MongoDB.

### 3. Verify Model Files

Ensure the trained model files are in the `model/` directory:
- `model.safetensors`
- `config.json`
- `label_info.json`
- `tokenizer.json`
- `tokenizer_config.json`
- `vocab.txt`

If missing, train the model using:
```bash
# Open and run the notebook
jupyter notebook scripts/model_training.ipynb
```

## 🎮 Usage

### Running the Complete System

#### 1. Start the MCP Server (in one terminal)

```bash
python api/mcp_server/mcp_server.py
```

You should see:
```
Loading model and tokenizer...
Model loaded successfully.
Connected to MongoDB database: ecommerce_support
Model and data loaded successfully. Initializing MCP server...
```

#### 2. Start the WhatsApp Bot (in another terminal)

```bash
python api/main.py
```

The bot will start on `http://localhost:8000`

#### 3. Setup ngrok (for local development)

```bash
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok-free.app`) and update:
1. Your WhatsApp app webhook URL
2. The `callback_url` in `api/main.py`

## 📁 Project Structure

```
E-com-Automated-Resolution/
├── api/
│   ├── main.py                          # WhatsApp bot entry point
│   ├── functions.py                     # Response generation logic
│   ├── db/
│   │   └── mongo.py                     # MongoDB connection & queries
│   ├── llm/
│   │   ├── groq_model.py               # Groq LLM with tool calling
│   │   └── conversation_context.py     # Context tracking system
│   ├── model/
│   │   └── multitask_distil_bert.py    # Custom DistilBERT model
│   ├── mcp_client/
│   │   ├── __init__.py
│   │   └── client.py                    # MCP client implementation
│   └── mcp_server/
│       └── mcp_server.py                # MCP server with tools
├── dashboard/                            # Customer support dashboard
│   ├── app.py                           # Streamlit dashboard app
│   ├── db_analytics.py                  # Analytics functions
│   └── requirements.txt                 # Dashboard dependencies
├── data/
│   ├── Ecommerce_Delivery_Analytics_New.csv
│   └── nlu_training_data.csv
├── model/                                # Trained model artifacts
│   ├── model.safetensors
│   ├── config.json
│   ├── label_info.json
│   └── tokenizer files...
├── scripts/
│   ├── label_data.ipynb                 # Data labeling notebook
│   ├── model_training.ipynb             # Model training notebook
│   ├── push_csv_to_mongo.py            # Database setup script
│   ├── simulate_whatsapp.py            # Testing script
│   └── test_mcp_integration.py         # MCP testing script
├── .env                                  # Environment variables (create this)
├── requirements.txt                      # Python dependencies
├── GUIDE.md                              # Detailed developer guide
└── README.md                             # This file
```

## 🔧 Components

### 1. WhatsApp Bot (`api/main.py`)
- Built with FastAPI and PyWa
- Handles webhook verification
- Receives and sends WhatsApp messages
- Saves conversation history to MongoDB

### 2. Response Generator (`api/functions.py`)
- **Smart NLU Caching**: Runs NLU analysis only when needed
  - First message from user
  - 24+ hours since last message (new session)
  - Otherwise uses cached result
- Retrieves user chat history from MongoDB
- Orchestrates LLM calls with tool support
- Updates NLU cache when topic changes
- Manages conversation flow

### 3. Groq LLM (`api/llm/groq_model.py`)
- **Model**: `moonshotai/kimi-k2-instruct-0905` (optimized for tool calling)
- **Intent-Driven**: Receives NLU results (intent + sentiment) with every message
- Implements tool calling protocol
- Maintains conversation context
- Makes intelligent decisions about tool usage
- Asks clarifying questions when information is missing

### 4. Conversation Context (`api/llm/conversation_context.py`)
- Tracks conversation state per user
- **NLU Result Caching**: Stores intent/sentiment to avoid re-analysis
- **Session Detection**: Detects 24h gaps for session renewal
- Stores extracted information (Order IDs, etc.)
- Tracks pending actions and questions asked
- Provides context summaries to LLM

### 5. MCP Client (`api/mcp_client/client.py`)
- Connects to MCP server via stdio
- **Persistent Connection**: Background event loop for efficient tool calling
- Provides synchronous tool wrappers for non-async code
- Handles tool execution and error handling
- Automatic reconnection on failures

### 6. MCP Server (`api/mcp_server/mcp_server.py`)
- Hosts three main tools (NLU, DB query, Refund processing)
- Loads trained NLU model once on startup
- Connects to MongoDB for real-time data
- Processes tool calls efficiently

### 7. NLU Model (`api/model/multitask_distil_bert.py`)
- Fine-tuned DistilBERT-base-uncased
- Multi-task learning: intent + sentiment
- High accuracy classification (90%+)
- Fast inference on CPU/GPU

### 8. MongoDB (`api/db/mongo.py`)
- Stores order details (`order_details` collection)
- Maintains chat history (`chats` collection)
- Provides query functions for order lookup

## 🛠️ Available Tools

### 1. `smart_triage_nlu`

Analyzes customer messages to classify intent and sentiment.

**When It's Called:**
- ✅ **First message** from user (always)
- ✅ **After 24+ hours** of inactivity (new session)
- ✅ **Topic changes** detected by LLM (e.g., switching from one order to another)
- ❌ **Follow-up messages** in same conversation (uses cache)

**Input:**
```json
{
  "text": "My order is delayed and I'm very upset!"
}
```

**Output:**
```json
{
  "intent": "report_delivery_delay",
  "intent_confidence": 0.9234,
  "sentiment": "negative",
  "sentiment_confidence": 0.8876
}
```

**Supported Intents:**
- `track_order` / `check_order_status`
- `report_delivery_delay`
- `report_order_content_issue`
- `request_refund`
- `provide_feedback_on_service`

**Supported Sentiments:**
- `positive`
- `negative`
- `neutral`

### 2. `query_order_database`

Retrieves order information from MongoDB.

**Input:**
```json
{
  "order_id": "ORD000001"
}
```

**Output:**
```json
{
  "Order ID": "ORD000001",
  "Platform": "JioMart",
  "Product Category": "Fruits & Vegetables",
  "Order Value (INR)": 382,
  "Order Date": "2023-01-15",
  "Delivery Status": "Delivered",
  "Service Rating": 5
}
```

### 3. `process_refund`

Processes refund requests (simulated in this version).

**Input:**
```json
{
  "order_id": "ORD000003",
  "amount": 599,
  "reason": "Items missing from delivery"
}
```

**Output:**
```json
{
  "status": "success",
  "transaction_id": "RFND_20250105123045_ORD000003",
  "amount_refunded": 599,
  "currency": "INR",
  "estimated_arrival": "3-5 business days"
}
```

### 4. `request_human_intervention`

Escalates complex issues to human customer support agents.

**When It's Called:**
- Customer explicitly asks to speak with a human
- Very frustrated customers (negative sentiment >90%)
- Issues outside automation scope
- Complex disputes requiring manual investigation
- Repeated resolution failures

**Input:**
```json
{
  "user_id": "1234567890",
  "reason": "Customer extremely frustrated with prolonged unresolved issue",
  "last_message": "This is unacceptable! I've been waiting for 2 weeks!",
  "priority": "high"
}
```

**Output:**
```json
{
  "status": "success",
  "alert_id": "677ad14c123456789abcdef0",
  "message": "Alert created and support team notified"
}
```

**Priority Levels:**
- `high`: Very frustrated customers, urgent issues
- `medium`: Standard complex issues, human requests
- `low`: General inquiries needing expertise

## 📊 Customer Support Dashboard

A real-time Streamlit dashboard for monitoring chatbot performance and managing human intervention alerts.

### Dashboard Features

#### 📈 Overview Tab
- **Key Metrics**: Users served, average response time, intervention rate, auto-resolution rate
- **Visual Analytics**:
  - Intent distribution (pie chart)
  - Service ratings (bar chart)
  - Response time trends (line chart)
- **Refund Statistics**: Total refunds processed and amounts

#### 🚨 Alerts Tab
- Real-time human intervention alerts
- Priority-based filtering (high/medium/low)
- Alert details: user ID, reason, timestamp, last message
- One-click resolve functionality
- Status tracking (pending/resolved)

#### 📊 Analytics Tab
- **Order Analytics**: Delivery delays, average order value
- **Platform Distribution**: Order breakdown by platform
- **Category Distribution**: Popular product categories
- **Refund Analysis**: Refund reasons and category breakdown

#### 💬 Conversations Tab
- Recent chat history with search
- User message tracking
- Conversation timeline

### Running the Dashboard

#### 1. Install Dashboard Dependencies

```bash
cd dashboard
pip install -r requirements.txt
```

#### 2. Start the Dashboard

```bash
streamlit run app.py
```

The dashboard will open in your browser at `http://localhost:8501`

#### 3. Dashboard Configuration

The dashboard automatically connects to your MongoDB instance using the credentials from your `.env` file. Make sure:
- MongoDB is accessible
- Collections exist: `order_details`, `chats`, `human_intervention_alerts`
- Data is populated (run `scripts/push_csv_to_mongo.py` if needed)

### Dashboard Features

- **Auto-refresh**: Updates every 30 seconds
- **Time Range Filters**: View data for last 24h, 7 days, or 30 days
- **Real-time Alerts**: See escalations as they happen
- **Interactive Charts**: Hover for detailed information
- **Resolve Alerts**: Mark alerts as resolved directly from dashboard

### Monitoring Best Practices

1. **Check alerts regularly**: Address pending interventions promptly
2. **Monitor response times**: Ensure bot is performing efficiently
3. **Track resolution rates**: High auto-resolution indicates good automation
4. **Review refund patterns**: Identify common issues for proactive improvement
5. **Analyze intent distribution**: Understand customer needs and bot usage

## 🧪 Testing

### Unit Tests

Run MCP integration tests:

```bash
python scripts/test_mcp_integration.py
```

Expected output:
```
Testing Smart Triage NLU...
✓ Intent: delivery_complaint
✓ Sentiment: negative

Testing Order Database Query...
✓ Order found: ORD000001
✓ Platform: JioMart

Testing Refund Processing...
✓ Refund successful
✓ Transaction ID generated
```

### Conversation Simulations

Test different scenarios:

```bash
# Test general conversation
python scripts/simulate_whatsapp.py

# Test order inquiry flow
python scripts/simulate_whatsapp.py --scenario order

# Test refund request flow
python scripts/simulate_whatsapp.py --scenario refund
```

### Manual Testing via WhatsApp

Send messages to your WhatsApp Business number:

**Example Conversations:**

1. **Order Inquiry:**
   ```
   You: Hi, where is my order?
   Bot: I'd be happy to help! Could you please share your Order ID?
   You: ORD000001
   Bot: I found your order! Here are the details...
   ```

2. **Refund Request:**
   ```
   You: I want a refund for ORD000003
   Bot: I found your order for ₹599. Would you like me to process a refund?
   You: Yes
   Bot: Refund processed successfully! Transaction ID: RFND_...
   ```

3. **General Inquiry:**
   ```
   You: What's your return policy?
   Bot: Our return policy allows returns within 30 days...
   ```

## 📊 Performance Metrics

- **NLU Model Accuracy**: ~90%+ on test set
- **Intent Classification**: F1-score > 0.88
- **Sentiment Analysis**: F1-score > 0.85
- **Response Time**: <2 seconds (with GPU)
- **Tool Call Success Rate**: ~95%


## 🙏 Acknowledgments

- **Groq** for providing fast LLM inference
- **Anthropic** for the Model Context Protocol (MCP)
- **Hugging Face** for Transformers library
- **PyWa** for WhatsApp integration
- **MongoDB** for database services

---
