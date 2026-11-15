import os
import httpx

EMBEDDING_BASE_URL = os.environ["EMBEDDING_BASE_URL"]
EMBEDDING_API_KEY = os.environ["EMBEDDING_API_KEY"]

def embed(texts:list[str], kind: str = "passage") -> list[list[float]]:
    response = httpx.post(
        EMBEDDING_BASE_URL,
        headers={"Authorization" : f"Bearer {EMBEDDING_API_KEY}"},
        json={"texts": texts, "kind": kind},
        timeout=30
    )
    response.raise_for_status()
    return response.json()["embeddings"]