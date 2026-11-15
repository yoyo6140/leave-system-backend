from sqlalchemy.orm import Session
from app.ai.client import embed
from app.models import KbChunk, KbDocument

def search(db: Session, query: str, top_k: int=5) ->list[dict]:
    query_vector = embed([query], kind="query")[0]

    results = (
        db.query(KbChunk, KbDocument.title)
        .join(KbDocument, KbChunk.document_id == KbDocument.id)
        .order_by(KbChunk.embedding.cosine_distance(query_vector))
        .limit(top_k)
        .all()
    )

    return [
        {
            "document_id": chunk.document_id,
            "document_title": title,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content
        }
        for chunk, title in results
    ]