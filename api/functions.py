import logging
import requests
import os
from dotenv import load_dotenv, find_dotenv

from api.llm.groq_model import call_groq_model

# configure module logger
logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())

VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
PAGE_ACCESS_TOKEN = os.getenv('PAGE_ACCESS_TOKEN')
API_VERSION = os.getenv('API_VERSION', 'v24.0')
# PAGE_ID = os.getenv('FB_PAGE_ID') or os.getenv('PAGE_ID')

def _send_message(psid: str, message: str, message_type: str):
    # logger.info("Sending message to %s: %s", psid, message)
    try:
        response = requests.post(
            url=f"https://graph.facebook.com/{API_VERSION}/me/messages",
            params={"access_token": PAGE_ACCESS_TOKEN},
            json={
                "recipient": {"id": psid},
                "message": {"text": message},
                "messaging_type": message_type,
            },
            timeout=5,
        )
        response.raise_for_status()
        # logger.debug("Facebook response: %s %s", response.status_code, response.text)
    except requests.RequestException as e:
        logger.exception("Failed to send message to Facebook: %s", e)

def generate_response(message: str, psid: str, message_type: str):
    # logger.info("Generating response for message: %s", message)
    try:
        answer = call_groq_model(message)
        _send_message(psid, answer, message_type)
    except Exception as e:
        logger.exception("Failed to generate response: %s", e)

def send_response(psid: str, message: str, message_type: str):
    _send_message(psid, message, message_type)