from groq import Groq
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

GROQ_API_KEY = os.getenv('GROQ_API_KEY')

prompt = """You are an AI assistant that helps people find information. Answer in a brief and concise manner."""

def call_groq_model(prompt: str) -> str:
    client = Groq(api_key=GROQ_API_KEY)
    completion = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {
                "role": "system",
                "content": prompt
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    answer = completion.choices[0].message.content
    return answer # type: ignore