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
print("Loading model and tokenizer... This may take a moment.", file=sys.stderr)
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
    print(f"Loaded {num_intent_labels} intents and {num_sentiment_labels} sentiments.", file=sys.stderr)
except FileNotFoundError:
    print("Error: 'label_info.json' not found in model directory.", file=sys.stderr)
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
    print("Model loaded successfully.", file=sys.stderr)
except Exception as e:
    print(f"Error loading model from {MODEL_PATH}.", file=sys.stderr)
    print("Please make sure you have run 'train_model.py' successfully.", file=sys.stderr)
    print(f"Error: {e}", file=sys.stderr)
    exit()

# 3. Connect to MongoDB and get order collection
print("Connecting to MongoDB...", file=sys.stderr)
mongo_client = get_mongo_client()
if mongo_client is None:
    print("Error: Failed to connect to MongoDB. Check MONGO_URI environment variable.", file=sys.stderr)
    exit()

db = mongo_client[DATABASE_NAME]
orders_collection = db.get_collection("order_details")
print(f"Connected to MongoDB database: {DATABASE_NAME}", file=sys.stderr)

print("\nModel and data loaded successfully. Initializing MCP server...", file=sys.stderr)

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
            name="check_refund_eligibility",
            description="Checks if an order is eligible for refund based on product category and calculates the refund amount. Food & Beverage items cannot be refunded. For eligible items, a 5% shipping fee is deducted from the order value. Returns eligibility status, refund amount, and reason.",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID to check for refund eligibility"
                    }
                },
                "required": ["order_id"]
            }
        ),
        types.Tool(
            name="process_refund",
            description="Processes a refund for an eligible order by updating the database. This should only be called after check_refund_eligibility confirms the order is eligible and the customer has approved the refund amount. Marks the order as refunded in the database.",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID to process refund for"
                    },
                    "amount": {
                        "type": "number",
                        "description": "The refund amount (should be the calculated amount from check_refund_eligibility)"
                    },
                    "reason": {
                        "type": "string",
                        "description": "The reason for the refund"
                    }
                },
                "required": ["order_id", "amount", "reason"]
            }
        ),
        types.Tool(
            name="request_human_intervention",
            description="Send an alert to the customer support dashboard when the chatbot cannot handle a request or when the user explicitly asks to speak with a human. This escalates the conversation to a human agent.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The user ID who needs human assistance"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for human intervention (e.g., 'Complex issue', 'User requested human', 'Unable to resolve')"
                    },
                    "last_message": {
                        "type": "string",
                        "description": "The last message from the user"
                    },
                    "priority": {
                        "type": "string",
                        "description": "Priority level: 'low', 'medium', or 'high'",
                        "enum": ["low", "medium", "high"]
                    }
                },
                "required": ["user_id", "reason", "last_message"]
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
        print(f"[Tool Call] smart_triage_nlu: '{text}'", file=sys.stderr)
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
            print(f"[Tool Result] {result}", file=sys.stderr)
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            print(f"Error in smart_triage_nlu: {e}", file=sys.stderr)
            return [types.TextContent(type="text", text=json.dumps({"error": str(e)}))]
    
    elif name == "query_order_database":
        order_id = arguments["order_id"]
        print(f"[Tool Call] query_order_database: '{order_id}'", file=sys.stderr)
        try:
            # Query MongoDB for the order
            order_data = orders_collection.find_one({"Order ID": order_id}, {"_id": 0})
            
            if order_data is None:
                print(f"[Tool Result] Order '{order_id}' not found.", file=sys.stderr)
                return [types.TextContent(type="text", text=json.dumps({"error": "Order ID not found."}))]
            
            # Convert any non-JSON-serializable types if needed
            result = {k: str(v) if isinstance(v, (pd.Timestamp,)) else v for k, v in order_data.items()}
            print(f"[Tool Result] Found order for {order_id}", file=sys.stderr)
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            print(f"Error in query_order_database: {e}", file=sys.stderr)
            return [types.TextContent(type="text", text=json.dumps({"error": str(e)}))]
    
    elif name == "check_refund_eligibility":
        order_id = arguments["order_id"]
        print(f"[Tool Call] check_refund_eligibility: '{order_id}'", file=sys.stderr)
        try:
            # Query MongoDB for the order
            order_data = orders_collection.find_one({"Order ID": order_id}, {"_id": 0})
            
            if order_data is None:
                print(f"[Tool Result] Order '{order_id}' not found.", file=sys.stderr)
                return [types.TextContent(type="text", text=json.dumps({
                    "eligible": False,
                    "error": "Order ID not found."
                }))]
            
            # Get product category and order value
            product_category = order_data.get("Product Category", "")
            order_value = float(order_data.get("Order Value (INR)", 0))
            
            # Check if product category is Food & Beverage (Beverages, Snacks, Dairy, Fruits & Vegetables, Grocery)
            food_beverage_categories = [
                "Beverages", "Snacks", "Dairy", "Fruits & Vegetables", "Grocery"
            ]
            
            is_food_beverage = product_category in food_beverage_categories
            
            if is_food_beverage:
                # Food & Beverage items cannot be refunded
                result = {
                    "eligible": False,
                    "order_id": order_id,
                    "product_category": product_category,
                    "order_value": order_value,
                    "reason": f"Food & Beverage items ({product_category}) cannot be refunded due to health and safety regulations.",
                    "message": f"I'm sorry, but we cannot process refunds for {product_category} items due to health and safety policies. Is there another way I can help you with this order?"
                }
                print(f"[Tool Result] Not eligible: Food & Beverage category", file=sys.stderr)
            else:
                # Eligible for refund - calculate refund amount (subtract 5% shipping fee)
                shipping_fee_percent = 0.05
                shipping_fee = order_value * shipping_fee_percent
                refund_amount = order_value - shipping_fee
                
                result = {
                    "eligible": True,
                    "order_id": order_id,
                    "product_category": product_category,
                    "order_value": order_value,
                    "shipping_fee": round(shipping_fee, 2),
                    "refund_amount": round(refund_amount, 2),
                    "message": f"Your order for {product_category} (₹{order_value}) is eligible for refund. After deducting the 5% shipping fee (₹{round(shipping_fee, 2)}), you will receive ₹{round(refund_amount, 2)}. Would you like to proceed with the refund?"
                }
                print(f"[Tool Result] Eligible: Refund amount = ₹{round(refund_amount, 2)}", file=sys.stderr)
            
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            print(f"Error in check_refund_eligibility: {e}", file=sys.stderr)
            return [types.TextContent(type="text", text=json.dumps({
                "eligible": False,
                "error": str(e)
            }))]
    
    elif name == "process_refund":
        order_id = arguments["order_id"]
        amount = arguments["amount"]
        reason = arguments["reason"]
        print(f"[Tool Call] process_refund: {order_id} for ₹{amount} due to '{reason}'", file=sys.stderr)
        try:
            # 1. Verify the order exists in MongoDB
            order_data = orders_collection.find_one({"Order ID": order_id})
            
            if order_data is None:
                print("[Tool Result] Refund failed: Order not found.", file=sys.stderr)
                return [types.TextContent(type="text", text=json.dumps({
                    "status": "failed", 
                    "error": "Order ID not found."
                }))]
            
            # 2. Check if already refunded
            if order_data.get("Refund Requested") == "Processed":
                print("[Tool Result] Refund failed: Order already refunded.", file=sys.stderr)
                return [types.TextContent(type="text", text=json.dumps({
                    "status": "failed",
                    "error": "This order has already been refunded."
                }))]
            
            # 3. Update the database to mark as refunded
            update_result = orders_collection.update_one(
                {"Order ID": order_id},
                {
                    "$set": {
                        "Refund Requested": "Processed",
                        "Refund Amount": amount,
                        "Refund Reason": reason,
                        "Refund Date": pd.Timestamp.now().isoformat()
                    }
                }
            )
            
            if update_result.modified_count == 0:
                print("[Tool Result] Refund failed: Database update failed.", file=sys.stderr)
                return [types.TextContent(type="text", text=json.dumps({
                    "status": "failed",
                    "error": "Failed to update database."
                }))]
            
            # 4. Generate transaction ID and return success
            transaction_id = f"RFND_{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}_{order_id}"
            result = {
                "status": "success",
                "transaction_id": transaction_id,
                "order_id": order_id,
                "amount_refunded": amount,
                "message": f"Refund processed successfully! ₹{amount} will be credited to your account within 5-7 business days. Transaction ID: {transaction_id}"
            }
            print(f"[Tool Result] {result}", file=sys.stderr)
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            print(f"Error in process_refund: {e}", file=sys.stderr)
            return [types.TextContent(type="text", text=json.dumps({
                "status": "failed",
                "error": str(e)
            }))]
    
    elif name == "request_human_intervention":
        user_id = arguments["user_id"]
        reason = arguments["reason"]
        last_message = arguments["last_message"]
        priority = arguments.get("priority", "medium")
        print(f"[Tool Call] request_human_intervention: {user_id} - {reason}", file=sys.stderr)
        try:
            # Create alert in MongoDB
            alert_data = {
                "user_id": user_id,
                "reason": reason,
                "last_message": last_message,
                "priority": priority,
                "status": "pending",
                "timestamp": pd.Timestamp.now().timestamp(),
                "created_at": pd.Timestamp.now().isoformat()
            }
            
            # Insert into human_intervention_alerts collection
            alerts_collection = db.get_collection("human_intervention_alerts")
            result = alerts_collection.insert_one(alert_data)
            
            response = {
                "status": "success",
                "alert_id": str(result.inserted_id),
                "message": f"Alert sent to customer support. A human agent will assist you shortly.",
                "user_id": user_id,
                "priority": priority
            }
            print(f"[Tool Result] Alert created: {response['alert_id']}", file=sys.stderr)
            return [types.TextContent(type="text", text=json.dumps(response, indent=2))]
            
        except Exception as e:
            print(f"Error in request_human_intervention: {e}", file=sys.stderr)
            return [types.TextContent(type="text", text=json.dumps({"error": str(e)}))]
    
    else:
        return [types.TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

async def main():
    """
    Initializes and runs the MCP server using stdio transport.
    """
    print("\n=======================================================", file=sys.stderr)
    print("MCP server is running and waiting for a client...", file=sys.stderr)
    print("This server exposes 5 tools:", file=sys.stderr)
    print("  - smart_triage_nlu(text: str)", file=sys.stderr)
    print("  - query_order_database(order_id: str)", file=sys.stderr)
    print("  - check_refund_eligibility(order_id: str)", file=sys.stderr)
    print("  - process_refund(order_id: str, amount: int, reason: str)", file=sys.stderr)
    print("  - request_human_intervention(user_id: str, reason: str, last_message: str, priority: str)", file=sys.stderr)
    print("=======================================================", file=sys.stderr)
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
