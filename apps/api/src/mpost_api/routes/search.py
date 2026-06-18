import json
import urllib.error
import urllib.request
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from mpost_api.config import settings
from mpost_api.db import get_db
from mpost_api.embeddings import format_vector, get_query_embedder
from mpost_api.repository import vector_search
from mpost_api.summary import summarize_chunks

router = APIRouter()


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=50)
    echelon: str | None = None
    mp_unit_type: str | None = None
    operation_type: str | None = None


class SearchResult(BaseModel):
    chunk_id: str
    chunk_index: int
    page_number: int | None = None
    document_id: str
    title: str
    title_description: str
    snippet: str
    score: float
    pdf_url: str
    metadata: dict[str, str | None] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    summary: str
    summary_source: str
    results: list[SearchResult]


@router.post("", response_model=list[SearchResult])
def search_documents(
    request: SearchRequest,
    db: Annotated[Session, Depends(get_db)],
) -> list[SearchResult]:
    query_embedding = get_query_embedder().encode_one(request.query)
    rows = vector_search(
        db,
        query_vector=format_vector(query_embedding),
        limit=request.limit,
        echelon=request.echelon,
        mp_unit_type=request.mp_unit_type,
        operation_type=request.operation_type,
    )

    # Generate titles for chunks
    results = [_search_result_from_row(row) for row in rows]
    if settings.llm_provider == "huggingface" and results:
        titles = _generate_chunk_titles(request.query, [r.snippet for r in results])
        for result, title in zip(results, titles):
            if title:
                result.title_description = title

    return results


@router.post("/summary", response_model=SearchResponse)
def search_documents_with_summary(
    request: SearchRequest,
    db: Annotated[Session, Depends(get_db)],
) -> SearchResponse:
    results = search_documents(request, db)
    summary, source = summarize_chunks(request.query, [result.snippet for result in results])
    return SearchResponse(summary=summary, summary_source=source, results=results)


def _search_result_from_row(row: dict[str, object]) -> SearchResult:
    return SearchResult(
        chunk_id=str(row["chunk_id"]),
        chunk_index=int(row["chunk_index"]),
        page_number=_optional_int(row.get("page_number")),
        document_id=str(row["document_id"]),
        title=str(row["title"]),
        title_description=_title_description(str(row["snippet"])),
        snippet=str(row["snippet"]),
        score=float(row["score"]),
        pdf_url=f"/documents/{row['document_id']}/file",
        metadata={
            "doctrine_type": _optional_str(row.get("doctrine_type")),
            "echelon": _optional_str(row.get("echelon")),
            "mp_unit_type": _optional_str(row.get("mp_unit_type")),
            "operation_type": _optional_str(row.get("operation_type")),
            "classification_level": _optional_str(row.get("classification_level")),
            "tags": ", ".join(row.get("tags") or []),
        },
    )


def _optional_str(value: object) -> str | None:
    return str(value) if value is not None else None


def _optional_int(value: object) -> int | None:
    return int(value) if value is not None else None


def _generate_chunk_titles(query: str, snippets: list[str]) -> list[str]:
    """Generate concise, informative titles for chunks using LLM."""
    if not snippets or not settings.hf_api_token:
        return [_title_description(s) for s in snippets]

    # Build a batch request for all chunks
    chunks_text = ""
    for i, snippet in enumerate(snippets[:10], 1):  # Limit to first 10 for performance
        preview = snippet[:300].replace('\n', ' ')
        chunks_text += f"\n{i}. {preview}\n"

    prompt = (
        f"You are analyzing military police doctrine search results for the query: '{query}'\n\n"
        "For each excerpt below, write a concise, informative title (max 12 words) that captures its main topic.\n"
        "Focus on the specific subject matter, not generic descriptions.\n"
        "Format: One title per line, numbered to match.\n\n"
        f"Excerpts:{chunks_text}\n"
        "Titles:"
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.hf_api_token}",
    }

    body = json.dumps({
        "model": settings.hf_model,
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 250,
        "temperature": 0.2,
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://router.huggingface.co/v1/chat/completions",
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
            if isinstance(result, dict) and "choices" in result:
                if len(result["choices"]) > 0:
                    content = result["choices"][0].get("message", {}).get("content", "").strip()
                    # Parse numbered titles
                    titles = []
                    for line in content.split('\n'):
                        line = line.strip()
                        # Remove numbering like "1. " or "1) "
                        if line and line[0].isdigit():
                            # Find where the actual title starts
                            title = line.split('. ', 1)[-1].split(') ', 1)[-1]
                            # Remove markdown formatting (bold, italics, etc)
                            title = title.replace('**', '').replace('__', '').replace('*', '').replace('_', '')
                            titles.append(title.strip()[:120])

                    # Pad with fallback titles if we didn't get enough
                    while len(titles) < len(snippets):
                        titles.append(_title_description(snippets[len(titles)]))

                    return titles[:len(snippets)]
    except Exception as e:
        print(f"Title generation error: {type(e).__name__}: {e}")

    # Fallback to extractive
    return [_title_description(s) for s in snippets]


def _title_description(snippet: str) -> str:
    """Generate a concise, informative title from the snippet."""
    import re

    cleaned = " ".join(snippet.split())
    if not cleaned:
        return "Relevant library excerpt"

    # Extract key phrases and generate a descriptive title
    # Look for section headers, definitions, or key statements

    # Check for headers/titles (often in ALL CAPS or Title Case at start)
    lines = snippet.split('\n')
    for line in lines[:3]:
        line = line.strip()
        if line and len(line) < 100:
            # Potential header if short and at start
            if line.isupper() or (line[0].isupper() and len(line.split()) <= 10):
                return line[:120].strip()

    # Look for definitions or key statements
    # Pattern: "X is/are/means..."
    definition_match = re.search(
        r'([A-Z][^.]+?(?:is|are|means|refers to|involves|includes|provides)[^.]+\.)',
        cleaned
    )
    if definition_match:
        return definition_match.group(1)[:120].strip()

    # Look for directive language (shall, must, should)
    directive_match = re.search(
        r'([A-Z][^.]*?(?:shall|must|should|will)[^.]+\.)',
        cleaned
    )
    if directive_match:
        return directive_match.group(1)[:120].strip()

    # Look for sentences with military terms
    key_terms = [
        'commander', 'mission', 'operations', 'responsibility', 'task',
        'military police', 'platoon', 'company', 'battalion', 'unit',
        'detention', 'security', 'support', 'planning', 'control'
    ]

    sentences = re.split(r'(?<=[.!?])\s+', cleaned)
    for sentence in sentences[:5]:
        sentence_lower = sentence.lower()
        if any(term in sentence_lower for term in key_terms):
            if len(sentence) >= 20:  # Substantial enough
                return sentence[:120].strip()

    # Fallback: use first complete sentence
    first_sentence = sentences[0] if sentences else cleaned
    return first_sentence[:120].strip()
