from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkRecord:
    text: str
    page_number: int | None = None


def chunk_text(text: str, max_chars: int = 1800, overlap: int = 200) -> list[str]:
    if max_chars <= overlap:
        raise ValueError("max_chars must be greater than overlap")

    normalized = " ".join(text.split())
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(normalized):
        end = min(start + max_chars, len(normalized))
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = end - overlap

    return chunks


def chunk_pages(pages: list[str], max_chars: int = 1800, overlap: int = 200) -> list[ChunkRecord]:
    records: list[ChunkRecord] = []
    for page_index, page_text in enumerate(pages, start=1):
        records.extend(
            ChunkRecord(text=chunk, page_number=page_index)
            for chunk in chunk_text(page_text, max_chars=max_chars, overlap=overlap)
        )
    return records
