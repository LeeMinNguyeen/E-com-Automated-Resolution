import logging
import requests
import os
from dotenv import load_dotenv, find_dotenv

from api.llm.groq_model import *
from api.db.mongo import *

# configure module logger
logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())

VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
PAGE_ACCESS_TOKEN = os.getenv('PAGE_ACCESS_TOKEN')
API_VERSION = os.getenv('API_VERSION', 'v24.0')
# PAGE_ID = os.getenv('FB_PAGE_ID') or os.getenv('PAGE_ID')

def _get_user_chat_history(user_id: str):
    """Retrieve chat history for a user from the database."""
    chat_history = get_chat_history(user_id)
    return chat_history

def save_message(user_id: str, from_role: str, to_role: str, text: str, timestamp: int):
    data = {
        "user_id": user_id,
        "from": from_role,
        "to": to_role,
        "text": text,
        "timestamp": timestamp
    }
    db = get_mongo_client()
    db, chat_collection = get_database() # type: ignore
    try:
        chat_collection.insert_one(data) # type: ignore
    except Exception as e:
        logger.exception("Failed to save message to MongoDB: %s", e)

    return True

def generate_response(user_id: str, message: str):
    # logger.info("Generating response for message: %s", message)
    try:
        chat_history = _get_user_chat_history(user_id)
        logger.info("Chat history for user %s: %s", user_id, chat_history)
        answer = call_groq_model(message, chat_history)
        return answer
    except Exception as e:
        logger.exception("Failed to generate response: %s", e)