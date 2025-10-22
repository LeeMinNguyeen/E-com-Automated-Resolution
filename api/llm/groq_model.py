from groq import Groq
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

GROQ_API_KEY = os.getenv('GROQ_API_KEY')

prompt = """You are an AI assistant that helps people find information. Answer in a brief and concise manner, keep your answer short because you are using WhatsApp. If you don't know the answer, just say that you don't know, don't try to make up an answer."""

def call_groq_model(user_message: str, history: list) -> str:
    client = Groq(api_key=GROQ_API_KEY)
    
    # Start with system message
    messages = [
        {
            "role": "system",
            "content": prompt
        }
    ]
    
    # Add chat history
    messages.extend(history)
    
    # Add current user message
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    completion = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=messages
    )
    answer = completion.choices[0].message.content
    return answer # type: ignore