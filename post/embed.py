import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]

load_dotenv(BASE_DIR / ".env") 
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def embed(text: str, *, model: str = "text-embedding-3-large") -> list[float]:
    text = (text or "").strip()
    if not text:
        return []
    r = client.embeddings.create(
        model=model,
        input=text,
    )
    return r.data[0].embedding
