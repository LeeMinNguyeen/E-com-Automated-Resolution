from fastapi import FastAPI, Request, Response
import uvicorn
import requests
import logging

from api.functions import generate_response, send_response

# use dotenv to handle .env
import os
from dotenv import load_dotenv, find_dotenv

# configure module logger; the app/uvicorn may reconfigure logging in prod
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())

VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
PAGE_ACCESS_TOKEN = os.getenv('PAGE_ACCESS_TOKEN')
API_VERSION = os.getenv('API_VERSION', 'v24.0')
# PAGE_ID = os.getenv('FB_PAGE_ID') or os.getenv('PAGE_ID')

app = FastAPI()

# receive messages Facebook sends to our webhook
@app.get('/webhook')
def init_messenger(request: Request):
	# FB sends the verify token as hub.verify_token
    fb_token = request.query_params.get("hub.verify_token")
    fb_mode = request.query_params.get("hub.mode")
    fb_challenge = request.query_params.get("hub.challenge")

    # we verify if the token sent matches our verify token
    if fb_mode == "subscribe" and fb_token == VERIFY_TOKEN:
    	# respond with hub.challenge parameter from the request.
        return Response(content=fb_challenge, status_code=200)
    return Response(content="Verification token mismatch", status_code=403)

@app.post('/webhook')
async def receive(request: Request):
    data = await request.json()
    logger.info("Received message: %s", data)

    match data.get("entry")[0]:
        # incoming message
        case {"messaging": [{"sender": {"id": psid}, "message": {"text": message_text}}]}:
            try:
                # Extract the PSID and message text from the incoming data
                psid = data.get("entry")[0].get("messaging")[0].get("sender").get("id")
                message_text = data.get("entry")[0].get("messaging")[0].get("message").get("text")

                if psid and message_text:
                    # TODO: Create and update database record for conversation history
                    # Send a response back to the user
                    generate_response(message_text, psid, "RESPONSE")
                else:
                    logger.warning("PSID or message text not found in the incoming data.")
            except Exception:
                logger.exception("Error processing incoming message data.")

        # reaction to message
        case {"messaging": [{"sender": {"id": psid}, "reaction": {"emoji": emoji}}]}:
            logger.info("Received reaction '%s' from PSID %s", emoji, psid)
            try:
                psid = data.get("entry")[0].get("messaging")[0].get("sender").get("id")
                emoji = data.get("entry")[0].get("messaging")[0].get("reaction").get("emoji")

                if psid and emoji:
                    # Acknowledge the reaction
                    send_response(psid, f"Received your reaction: {emoji}", "RESPONSE")
            except Exception:
                logger.exception("Error processing incoming reaction data.")

        case _:
            logger.warning("Unhandled message type: %s", data.get("entry")[0])

    return Response(status_code=200)

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)