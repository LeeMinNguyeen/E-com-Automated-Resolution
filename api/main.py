from fastapi import FastAPI, Request, Response
import uvicorn
import requests
import logging
from pywa import WhatsApp, types

from api.functions import *

# use dotenv to handle .env
import os
from dotenv import load_dotenv, find_dotenv
from datetime import datetime, timezone

# configure module logger; the app/uvicorn may reconfigure logging in prod
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())

VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
APP_ID = os.getenv('APP_ID')
APP_SECRET = os.getenv('APP_SECRET')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
PHONE_ID = os.getenv('PHONE_ID')

app = FastAPI()

# Create a WhatsApp client
wa = WhatsApp(
    phone_id=PHONE_ID,
    token=ACCESS_TOKEN,
    server=app, # the server to listen to incoming updates
    callback_url="https://letha-postethmoid-sharee.ngrok-free.dev",  # the public URL of your server
    verify_token=VERIFY_TOKEN, # some random string to verify the webhook
    app_id=APP_ID, # your app id
    app_secret=APP_SECRET # your app secret
)

# receive messages Facebook sends to our webhook
@app.get('/webhook')
def init(request: Request):
	# FB sends the verify token as hub.verify_token
    token = request.query_params.get("hub.verify_token")
    mode = request.query_params.get("hub.mode")
    challenge = request.query_params.get("hub.challenge")

    # we verify if the token sent matches our verify token
    if mode == "subscribe" and token == VERIFY_TOKEN:
    	# respond with hub.challenge parameter from the request.
        return Response(content=challenge, status_code=200)
    return Response(content="Verification token mismatch", status_code=403)

@wa.on_message
def receive(_: WhatsApp, msg: types.Message):
    logger.info("Received message: %s", msg)
    
    match msg.type:
        case "text":

            response_text = generate_response(msg.from_user.wa_id, msg.text)
            
            msg.reply(response_text)

            # save user message
            save_message(msg.from_user.wa_id, "user", "system", msg.text, msg.timestamp)
            # save the bot response
            save_message(msg.from_user.wa_id, "system", msg.from_user.wa_id, response_text, datetime.now().isoformat())

        case "reaction":
            logger.info("Received reaction: %s", msg.reaction)
            # handle reaction
            # msg.reply(f"Thanks for your reaction, {msg.from_user.name}!")

        case _:
            logger.warning("Unsupported message type: %s", msg.type)
            msg.reply("Sorry, I can only process text messages and reactions for now.")

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)