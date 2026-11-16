import os
import httpx

EMBEDDING_BASE_URL = os.environ["EMBEDDING_BASE_URL"]
EMBEDDING_API_KEY = os.environ["EMBEDDING_API_KEY"]
BATCH_SIZE = 64

def embed(texts:list[str], kind: str = "passage") -> list[list[float]]:
    embeddings =[]
    for i in range(0, len(texts), BATCH_SIZE):
        batch =texts[i:i + BATCH_SIZE]
        response = httpx.post(
            EMBEDDING_BASE_URL,
            headers={"Authorization" : f"Bearer {EMBEDDING_API_KEY}"},
            json={"texts": batch, "kind": kind},
            timeout=30
        )
        response.raise_for_status()
        embeddings.extend(response.json()["embeddings"])
    return embeddings