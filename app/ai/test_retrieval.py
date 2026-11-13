from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.ai.retrieval import search

db = SessionLocal()
results = search(db, "特休有幾天", top_k=3)

for r in results:
    print(f"[{r['document_title']}] chunk {r['chunk_index']}: {r['content'][:60]}")
    db.close()