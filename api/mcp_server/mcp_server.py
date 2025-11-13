import asyncio
import json
import os
import sys
import pandas as pd
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel
from dotenv import load_dotenv, find_dotenv

# Add parent directory to path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # Go up two levels to project root
sys.path.insert(0, PROJECT_ROOT)

from mcp.server.stdio import stdio_server
from mcp.server import Server
from mcp import types
from api.model.multitask_distil_bert import MultiTaskDistilBert # Import your custom model class
from api.db.mongo import get_mongo_client, DATABASE_NAME

# Load environment variables
load_dotenv(find_dotenv())

# --- Configuration ---
MODEL_PATH = os.path.join(PROJECT_ROOT, 'model')

# --- Global Variables (Loaded once on startup) ---
print("Loading model and tokenizer... This may take a moment.")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 1. Load the label mappings first (needed for model initialization)
try:
    with open(os.path.join(MODEL_PATH, 'label_info.json'), 'r') as f:
        label_info = json.load(f)
    
    # Create "inverse" mappings to convert model IDs back to text labels
    INTENT_MAP = {v: k for k, v in label_info['intent_labels'].items()}
    SENTIMENT_MAP = {v: k for k, v in label_info['sentiment_labels'].items()}
    num_intent_labels = len(INTENT_MAP)
    num_sentiment_labels = len(SENTIMENT_MAP)
    print(f"Loaded {num_intent_labels} intents and {num_sentiment_labels} sentiments.")
except FileNotFoundError:
    print("Error: 'label_info.json' not found in model directory.")
    exit()

# 2. Load the trained NLU model and tokenizer
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    # We must load our custom MultiTaskDistilBert class with the correct number of labels
    nlu_model = MultiTaskDistilBert.from_pretrained(
        MODEL_PATH,
        num_intent_labels=num_intent_labels,
        num_sentiment_labels=num_sentiment_labels
    ).to(device)
    nlu_model.eval() # Set model to evaluation mode
    print("Model loaded successfully.")
except Exception as e:
    print(f"Error loading model from {MODEL_PATH}.")
    print("Please make sure you have run 'train_model.py' successfully.")
    print(f"Error: {e}")
    exit()

# 3. Connect to MongoDB and get order collection
print("Connecting to MongoDB...")
mongo_client = get_mongo_client()
if mongo_client is None:
    print("Error: Failed to connect to MongoDB. Check MONGO_URI environment variable.")
    exit()

db = mongo_client[DATABASE_NAME]
orders_collection = db.get_collection("order_details")
print(f"Connected to MongoDB database: {DATABASE_NAME}")

print("\nModel and data loaded successfully. Initializing MCP server...")

# --- Define the Server and its Tools ---

# Initialize the MCP server
app = Server("ecommerce-agent-server")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """
    List all available tools for the MCP server.
    """
    return [
        types.Tool(
            name="smart_triage_nlu",
            description="Runs the trained multi-task NLU model to classify the user's intent and sentiment from their text. This is the 'Smart Triage' tool.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The user's input text to analyze"
                    }
                },
                "required": ["text"]
            }
        ),
        types.Tool(
            name="query_order_database",
            description="Looks up an order by its ID in the e-commerce database. Returns the order's details.",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID to look up"
                    }
                },
                "required": ["order_id"]
            }
        ),
        types.Tool(
            name="process_refund",
            description="Simulates processing a refund for a given order. In a real app, this would trigger a payment API.",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID to process refund for"
                    },
                    "amount": {
                        "type": "number",
                        "description": "The refund amount"
                    },
                    "reason": {
                        "type": "string",
                        "description": "The reason for the refund"
                    }
                },
                "required": ["order_id", "amount", "reason"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """
    Handle tool calls from the MCP client.
    """
    if name == "smart_triage_nlu":
        text = arguments["text"]
        print(f"[Tool Call] smart_triage_nlu: '{text}'")
        try:
            inputs = tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=128
            ).to(device)

            with torch.no_grad():
                intent_logits, sentiment_logits = nlu_model(**inputs)
            
            # Get probabilities (softmax) and the final prediction (argmax)
            intent_probs = F.softmax(intent_logits, dim=1)
            intent_pred_id = torch.argmax(intent_probs, dim=1).item()
            intent_confidence = intent_probs[0, intent_pred_id].item()
            
            sentiment_probs = F.softmax(sentiment_logits, dim=1)
            sentiment_pred_id = torch.argmax(sentiment_probs, dim=1).item()
            sentiment_confidence = sentiment_probs[0, sentiment_pred_id].item()

            # Convert IDs back to string labels
            result = {
                "intent": INTENT_MAP.get(intent_pred_id, "unknown"),
                "intent_confidence": round(intent_confidence, 4),
                "sentiment": SENTIMENT_MAP.get(sentiment_pred_id, "unknown"),
                "sentiment_confidence": round(sentiment_confidence, 4)
            }
            print(f"[Tool Result] {result}")
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            print(f"Error in smart_triage_nlu: {e}")
            return [types.TextContent(type="text", text=json.dumps({"error": str(e)}))]
    
    elif name == "query_order_database":
        order_id = arguments["order_id"]
        print(f"[Tool Call] query_order_database: '{order_id}'")
        try:
            # Query MongoDB for the order
            order_data = orders_collection.find_one({"Order ID": order_id}, {"_id": 0})
            
            if order_data is None:
                print(f"[Tool Result] Order '{order_id}' not found.")
                return [types.TextContent(type="text", text=json.dumps({"error": "Order ID not found."}))]
            
            # Convert any non-JSON-serializable types if needed
            result = {k: str(v) if isinstance(v, (pd.Timestamp,)) else v for k, v in order_data.items()}
            print(f"[Tool Result] Found order for {order_id}")
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            print(f"Error in query_order_database: {e}")
            return [types.TextContent(type="text", text=json.dumps({"error": str(e)}))]
    
    elif name == "process_refund":
        order_id = arguments["order_id"]
        amount = arguments["amount"]
        reason = arguments["reason"]
        print(f"[Tool Call] process_refund: {order_id} for {amount} due to '{reason}'")
        try:
            # --- Simulation ---
            # 1. Verify the order exists in MongoDB
            order_data = orders_collection.find_one({"Order ID": order_id})
            
            if order_data is None:
                print("[Tool Result] Refund failed: Order not found.")
                return [types.TextContent(type="text", text=json.dumps({"status": "failed", "error": "Order ID not found."}))]
            
            # 2. (Simulate) Update our database to show refund is processed
            # orders_collection.update_one(
            #     {"Order ID": order_id},
            #     {"$set": {"Refund Requested": "Processed"}}
            # )
            
            # 3. (Simulate) Return a success message with a fake transaction ID
            transaction_id = f"RFND_{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}_{order_id}"
            result = {
                "status": "success",
                "transaction_id": transaction_id,
                "order_id": order_id,
                "amount_refunded": amount,
                "message": "Refund processed successfully."
            }
            print(f"[Tool Result] {result}")
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            print(f"Error in process_refund: {e}")
            return [types.TextContent(type="text", text=json.dumps({"error": str(e)}))]
    
    else:
        return [types.TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

async def main():
    """
    Initializes and runs the MCP server using stdio transport.
    """
    print("\n=======================================================")
    print("MCP server is running and waiting for a client...")
    print("This server exposes 3 tools:")
    print("  - smart_triage_nlu(text: str)")
    print("  - query_order_database(order_id: str)")
    print("  - process_refund(order_id: str, amount: int, reason: str)")
    print("=======================================================")
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
