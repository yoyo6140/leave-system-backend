import re

# 檢查 長度太長 分段切片
def _split_long_text(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

# 切片type判斷 切法不同
def split_into_chunks( text: str, max_chars: int = 500, overlap: int = 50, doc_type: str="rule") -> list[str]:
    if doc_type == "letter":
        candidates = [text.strip()]
    elif doc_type == "raw":
        candidates = [p.strip() for p in re.split(r'(?=第\s*[一二三四五六七八九十0-9]+\s*條)', text) if p.strip()]
    else:
        candidates = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    for candidate in candidates:
        chunks.extend(_split_long_text(candidate, max_chars, overlap))
    return chunks