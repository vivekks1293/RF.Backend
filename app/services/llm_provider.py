import os
import json
from groq import Groq
import google.generativeai as genai
from openai import OpenAI

# ── Load config ───────────────────────────────────────────────────────────────
with open("config.json", "r") as f:
    CONFIG = json.load(f)


# ── Groq ──────────────────────────────────────────────────────────────────────
def run_groq(prompt):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model=CONFIG["groq"]["model"],
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    print(f">>> [GROQ] Response preview: {response.choices[0].message.content[:100]}")
    return response.choices[0].message.content


# ── Gemini ────────────────────────────────────────────────────────────────────
def run_gemini(prompt):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel(CONFIG["gemini"]["model"])
    response = model.generate_content(prompt)
    print(f">>> [Gemini] Response preview: {response.text[:100]}")
    return response.text


# ── OpenAI ────────────────────────────────────────────────────────────────────
def run_openai(prompt):
    client = OpenAI(api_key=os.getenv("OPEN_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content


# ── Router ────────────────────────────────────────────────────────────────────
def run_llm(prompt):
    provider = CONFIG["provider"]

    if provider == "groq":
        return run_groq(prompt)
    elif provider == "openai":
        return run_openai(prompt)
    elif provider == "gemini":
        return run_gemini(prompt)
    else:
        raise ValueError(f"Invalid provider: '{provider}'. Must be groq, openai or gemini.")