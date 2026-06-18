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

router = APIRouter()


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)
    max_history: int = Field(default=10, ge=0, le=20)


class ChatResponse(BaseModel):
    response: str
    sources: list[dict] = Field(default_factory=list)


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Annotated[Session, Depends(get_db)],
) -> ChatResponse:
    """Chat with the military police doctrine knowledge base."""

    # Get relevant context from vector search
    query_embedding = get_query_embedder().encode_one(request.message)
    search_results = vector_search(
        db,
        query_vector=format_vector(query_embedding),
        limit=5,
        echelon=None,
        mp_unit_type=None,
        operation_type=None,
    )

    # Build context from search results
    context_chunks = []
    sources = []
    for row in search_results:
        chunk_text = str(row["snippet"])[:500]
        context_chunks.append(chunk_text)
        sources.append({
            "document_id": str(row["document_id"]),
            "title": str(row["title"]),
            "page_number": row.get("page_number"),
            "score": float(row["score"]),
        })

    context = "\n\n---\n\n".join(context_chunks) if context_chunks else "No relevant information found."

    # Build conversation history (limit to recent messages)
    conversation_history = request.history[-request.max_history:] if request.history else []

    # Generate response
    response_text = _generate_chat_response(request.message, context, conversation_history)

    return ChatResponse(
        response=response_text,
        sources=sources,
    )


def _generate_chat_response(
    user_message: str,
    context: str,
    history: list[ChatMessage],
) -> str:
    """Generate a chat response using HF Inference API with RAG context."""

    if not settings.hf_api_token:
        return "Chat is not available (no HF API token configured)."

    # System prompt for RAG chat
    system_message = (
        "You are a knowledgeable assistant helping Military Police staff officers. "
        "Answer questions using the provided doctrine excerpts from official military police publications. "
        "Be concise but thorough. If the excerpts don't contain relevant information, say so. "
        "Use military terminology appropriately. Cite specific procedures or guidelines when applicable."
    )

    # Build messages array
    messages = [{"role": "system", "content": system_message}]

    # Add conversation history
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})

    # Add current user message with context
    user_message_with_context = (
        f"User question: {user_message}\n\n"
        f"Relevant doctrine excerpts:\n{context}\n\n"
        "Answer based on the excerpts above:"
    )
    messages.append({"role": "user", "content": user_message_with_context})

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.hf_api_token}",
    }

    # Use a fast model - DeepSeek V4 Flash or Llama 3.1 8B
    chat_model = "deepseek-ai/DeepSeek-V4-Flash"  # Fast and good quality

    body = json.dumps({
        "model": chat_model,
        "messages": messages,
        "max_tokens": 500,
        "temperature": 0.4,
        "top_p": 0.9,
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://router.huggingface.co/v1/chat/completions",
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

            if isinstance(result, dict) and "choices" in result:
                if len(result["choices"]) > 0:
                    message = result["choices"][0].get("message", {})
                    response_text = message.get("content", "").strip()
                    return response_text if response_text else "I couldn't generate a response."

            return "Error: Unexpected response format from AI model."

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "Unknown error"
        print(f"Chat API error {e.code}: {error_body}")
        return f"Error communicating with AI service (HTTP {e.code})."
    except Exception as e:
        print(f"Chat error: {type(e).__name__}: {e}")
        return "Error: Unable to generate response. Please try again."
