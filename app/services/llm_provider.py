import os
import json
import google.generativeai as genai
from openai import OpenAI
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

with open("config.json", "r") as f:
    CONFIG = json.load(f)

def run_openai(promt):
    pass

def run_gemini(promt):
    pass

def run_groc(promt):
    client = Groq(api_key = os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": promt}
        ]
    )
    raw = response.choices[0].message.content
    return raw

def run_llm(promt):
    provider = CONFIG["provider"]

    if provider == "openai":
        return run_openai(promt)
    if provider == "groq":
        return run_groc(promt)
    elif provider == "gemini":
        conversation_text = "\n".join(
            f"{m['role']: {m['content']}} " for m in promt
        )
        return run_gemini(conversation_text)
    else:
        print("Invalid provide!!")