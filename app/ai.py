"""
AI Service Layer.

Handles interactions with:
1. Embedding API (text-embedding-3-small via OpenAI Compatible API)
2. Vector Database (ChromaDB)
3. LLM Chat API
"""

import os
import httpx
import chromadb
from chromadb.config import Settings

# Load config
CHROMA_HOST = os.getenv("CHROMA_DB_HOST", "vectordb")
CHROMA_PORT = int(os.getenv("CHROMA_DB_PORT", 8000))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "image_gallery")

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_BASE = os.getenv("LLM_API_BASE")
# Chat Model
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
# Embedding Model
EMBEDDING_MODEL = "text-embedding-3-small"

# Global instances
_chroma_client = None
_chroma_collection = None

def get_chroma_collection():
    """
    Connects to ChromaDB and retrieves the collection.
    """
    global _chroma_client, _chroma_collection
    if _chroma_collection is None:
        try:
            _chroma_client = chromadb.HttpClient(
                host=CHROMA_HOST, 
                port=CHROMA_PORT,
                settings=Settings(anonymized_telemetry=False)
            )
            # Retrieve or create collection. 
            # We don't provide an embedding function here because we handle embeddings manually.
            _chroma_collection = _chroma_client.get_or_create_collection(name=COLLECTION_NAME)
        except Exception as e:
            print(f"Failed to connect to ChromaDB: {e}")
            raise e
    return _chroma_collection

def generate_embedding(text: str) -> list[float]:
    """
    Converts text to a vector embedding using remote API.
    Synchronous implementation for Celery tasks.
    """
    if not text:
        return []

    url = f"{LLM_API_BASE}/embeddings"
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "input": text,
        "model": EMBEDDING_MODEL
    }

    # Using sync client for simplicity in Celery workers
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            # OpenAI API format: data['data'][0]['embedding']
            return data["data"][0]["embedding"]
    except Exception as e:
        print(f"Embedding API Error: {e}")
        # Return a zero-vector or raise error depending on policy.
        # Here we raise to let Celery retry.
        raise e

async def query_llm(prompt: str) -> str:
    """
    Calls the external LLM API for Chat.
    """
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful photo gallery assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(f"{LLM_API_BASE}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"LLM API Error: {e}")
            return "Sorry, I couldn't process your request at the moment."