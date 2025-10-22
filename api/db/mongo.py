import os
from dotenv import load_dotenv, find_dotenv
from pymongo import MongoClient, errors
import logging
from datetime import datetime, timezone

load_dotenv(find_dotenv())

MONGO_URI = os.getenv("MONGO_URI", "")
DATABASE_NAME = "grocery_shipping"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_mongo_client():
    """Establish and return a MongoDB client."""
    try:
        client = MongoClient(MONGO_URI)
        # Test the connection
        client.admin.command('ping')
        return client
    except errors.ConnectionFailure as e:
        logger.exception("ERROR CONNECTING TO MONGODB: Please check MONGO_URI and Access List. Details: %s", e)
        return None

def get_database():
    """Get database connection and collections."""
    client = get_mongo_client()
    if client is None:
        return None, None, None
    
    db = client[DATABASE_NAME]
    chat_collection = db.get_collection("chat_history")

    return db, chat_collection

def get_chat_history(user_id: str, limit: int = 20):
    """Retrieve chat history for a user formatted for Groq API."""
    db, chat_collection = get_database()
    if chat_collection is None:
        return []

    # Fetch chat history from the database
    chat_docs = list(chat_collection.find({"user_id": user_id}).limit(limit))
    
    # Sort by timestamp in Python to handle mixed datetime types
    def get_sort_key(doc):
        ts = doc.get("timestamp")
        if isinstance(ts, str):
            # Parse ISO format string to datetime
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            return dt.timestamp()  # Convert to Unix timestamp (float)
        elif isinstance(ts, datetime):
            # Make naive datetime timezone-aware (assume UTC) then convert to timestamp
            if ts.tzinfo is None:
                dt = ts.replace(tzinfo=timezone.utc)
            else:
                dt = ts
            return dt.timestamp()  # Convert to Unix timestamp (float)
        return 0  # Fallback for missing timestamps
    
    chat_docs.sort(key=get_sort_key)
    
    # Format chat history for Groq API
    formatted_history = []
    for doc in chat_docs:
        # Determine role based on 'from' field
        if doc.get("from") == "system":
            role = "assistant"
        else:
            role = "user"
        
        # Add message with appropriate role
        if doc.get("text"):
            formatted_history.append({
                "role": role,
                "content": doc["text"]
            })
    
    return formatted_history

def delete_session(user_id: str):
    """Delete all messages for a specific user."""
    pass
    
if __name__ == "__main__":
    client = get_mongo_client()
    if client:
        db = client[DATABASE_NAME]
        logger.info("Successfully connected to database: %s", DATABASE_NAME)
    else:
        logger.error("Failed to connect to MongoDB.")