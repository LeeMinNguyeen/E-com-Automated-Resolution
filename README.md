# E-commerce Automated Resolution System

An intelligent WhatsApp chatbot for automated e-commerce customer support powered by AI. This system combines a fine-tuned DistilBERT model for natural language understanding with Groq's LLM for conversational AI, using the Model Context Protocol (MCP) for tool orchestration.

## System Flow

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
uvicorn api.main:app --reload
```

The bot will start on `http://localhost:8000`

#### 3. Setup ngrok (for local development)

```bash
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok-free.app`) and update:
1. Your WhatsApp app webhook URL
2. The `callback_url` in `api/main.py`

### Running the Dashboard

#### 1. Install Dashboard Dependencies

```bash
cd dashboard
pip install -r requirements.txt
```

#### 2. Start the Dashboard

```bash
streamlit run dashboard/app.py
```

The dashboard will open in your browser at `http://localhost:8501`

#### 3. Dashboard Configuration

The dashboard automatically connects to your MongoDB instance using the credentials from your `.env` file. Make sure:
- MongoDB is accessible
- Collections exist: `order_details`, `chats`, `human_intervention_alerts`
- Data is populated (run `scripts/push_csv_to_mongo.py` if needed)

## 📊 Performance Metrics

- Intent Accuracy:          88.89%
- Intent F1-Score:          0.8989
- Sentiment Accuracy:       97.78%
- Sentiment F1-Score:       0.9779
- Avg Intent Confidence:    0.9713
- Avg Sentiment Confidence: 0.9724
