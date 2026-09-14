def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> list[str]:
    text = (text or '').strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunks.append(text[start:end])
        if end >= n:
            break
        start = max(0, end - overlap)
    return chunks
