import json
import re
import urllib.error
import urllib.request

from mpost_api.config import settings


def summarize_chunks(query: str, chunks: list[str]) -> tuple[str, str]:
    unique_chunks = list(dict.fromkeys(chunks))
    if not unique_chunks:
        return "No relevant chunks were found.", "fallback"

    print(f"[Summary] Provider: {settings.llm_provider}")

    if settings.llm_provider == "huggingface":
        print(f"[Summary] Trying HF model: {settings.hf_model}")
        summary = _huggingface_summary(query, unique_chunks)
        if summary:
            return summary, settings.hf_model

    if settings.llm_provider == "ollama":
        print(f"[Summary] Trying Ollama: {settings.ollama_url} / {settings.ollama_model}")
        summary = _ollama_summary(query, unique_chunks)
        if summary:
            print("[Summary] Ollama succeeded!")
            return summary, settings.ollama_model
        else:
            print("[Summary] Ollama returned None")

    print("[Summary] Falling back to extractive")
    return _extractive_summary(query, unique_chunks), "extractive"


def _ollama_summary(query: str, chunks: list[str]) -> str | None:
    """Generate LLM-based summary using Ollama."""
    # Use more chunks with better context
    context_chunks = []
    total_chars = 0
    max_chars = 4000

    for chunk in chunks[:10]:
        chunk_text = chunk.strip()
        if total_chars + len(chunk_text) < max_chars:
            context_chunks.append(chunk_text)
            total_chars += len(chunk_text)
        else:
            break

    context = "\n\n---\n\n".join(context_chunks)

    # Improved prompt for military doctrine context
    prompt = (
        "You are assisting a Military Police staff officer. Based on the doctrine excerpts below, "
        "provide a focused executive summary that directly answers the question.\n\n"
        "Requirements:\n"
        "- Write 3-4 concise bullet points\n"
        "- Focus on actionable guidance, procedures, and key principles\n"
        "- Use military terminology appropriately\n"
        "- Be specific - cite relevant doctrine elements, echelons, or procedures when mentioned\n"
        "- If the excerpts discuss different aspects, organize by theme\n\n"
        f"Question: {query}\n\n"
        f"Doctrine Excerpts:\n{context}\n\n"
        "Executive Summary:"
    )

    body = json.dumps(
        {
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "num_predict": 300,
            },
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{settings.ollama_url.rstrip('/')}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (TimeoutError, urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"Ollama API error: {type(e).__name__}: {e}")
        return None

    response_text = str(payload.get("response") or "").strip()
    if not response_text:
        return None

    # Clean up the response
    return _clean_llm_response(response_text)


def _huggingface_summary(query: str, chunks: list[str]) -> str | None:
    """Generate LLM-based summary using Hugging Face Inference API."""
    # Build context from chunks
    context_chunks = []
    total_chars = 0
    max_chars = 3000  # HF free tier has limits

    for chunk in chunks[:8]:
        chunk_text = chunk.strip()
        if total_chars + len(chunk_text) < max_chars:
            context_chunks.append(chunk_text)
            total_chars += len(chunk_text)
        else:
            break

    context = "\n\n---\n\n".join(context_chunks)

    # Build system and user messages for chat completion
    num_chunks = len(context_chunks)
    system_message = (
        "You are assisting a Military Police staff officer. "
        "Analyze the provided doctrine excerpts and create a focused executive summary. "
        "Write 3-4 concise bullet points that synthesize the most important information. "
        "Focus on actionable guidance, procedures, and key principles. "
        "Use military terminology appropriately and be specific."
    )

    user_message = (
        f"Question: {query}\n\n"
        f"Below are the top {num_chunks} most relevant excerpts from military police doctrine. "
        f"Summarize the key points that directly answer the question.\n\n"
        f"Doctrine Excerpts:\n{context}\n\n"
        "Executive Summary (3-4 bullet points):"
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.hf_api_token}",
    }

    body = json.dumps({
        "model": settings.hf_model,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": 300,
        "temperature": 0.3,
        "top_p": 0.9,
    }).encode("utf-8")

    # Use Hugging Face Inference Providers API (new endpoint)
    api_url = "https://router.huggingface.co/v1/chat/completions"

    request = urllib.request.Request(
        api_url,
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "No error body"
        print(f"HF API HTTPError {e.code}: {error_body}")
        return None
    except (TimeoutError, urllib.error.URLError, json.JSONDecodeError) as e:
        # Model might be loading (cold start), return None to fall back
        print(f"HF API error: {type(e).__name__}: {e}")
        return None

    # Handle chat completion response format
    if isinstance(result, dict) and "choices" in result:
        if len(result["choices"]) > 0:
            message = result["choices"][0].get("message", {})
            response_text = message.get("content", "").strip()
        else:
            return None
    else:
        return None

    if not response_text:
        return None

    return _clean_llm_response(response_text)


def _clean_llm_response(text: str) -> str:
    """Clean and format LLM response."""
    # Remove common artifacts
    text = re.sub(r'^(Executive Summary:?|Summary:?)\s*', '', text, flags=re.IGNORECASE)
    text = text.strip()

    # Ensure bullet points are properly formatted
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Normalize bullet points
        if re.match(r'^[\d\*\-\•]', line):
            line = re.sub(r'^[\d\.\)\*\•]\s*', '• ', line)
        elif line and not line.startswith('•'):
            line = '• ' + line
        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


def _extractive_summary(query: str, chunks: list[str]) -> str:
    """Generate extractive summary by identifying most relevant sentences."""
    query_terms = set(_extract_key_terms(query.lower()))

    # Score and extract relevant sentences
    scored_sentences = []

    for chunk in chunks[:8]:
        sentences = _split_sentences(chunk)
        for sentence in sentences:
            if len(sentence.split()) < 5:  # Skip very short sentences
                continue

            score = _score_sentence(sentence, query_terms)
            if score > 0:
                scored_sentences.append((score, sentence))

    # Sort by score and take top sentences
    scored_sentences.sort(reverse=True, key=lambda x: x[0])

    # Build summary from top sentences, avoiding redundancy
    summary_sentences = []
    used_words = set()

    for score, sentence in scored_sentences[:8]:
        sentence_words = set(sentence.lower().split())
        # Check for redundancy
        overlap = len(sentence_words & used_words)
        if overlap < len(sentence_words) * 0.6:  # Less than 60% overlap
            summary_sentences.append(sentence)
            used_words.update(sentence_words)

        if len(summary_sentences) >= 4:
            break

    if not summary_sentences:
        return "Relevant excerpts were found. Review the search results below for details."

    # Format as bullet points
    bullets = []
    for sentence in summary_sentences[:4]:
        cleaned = sentence.strip()
        if not cleaned.endswith('.'):
            cleaned += '.'
        bullets.append(f"• {cleaned}")

    return '\n'.join(bullets)


def _extract_key_terms(text: str) -> list[str]:
    """Extract key terms from query, filtering common words."""
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'should', 'could', 'may', 'might', 'must', 'can', 'what',
        'when', 'where', 'which', 'who', 'how', 'why'
    }

    words = re.findall(r'\b[a-z]+\b', text.lower())
    return [w for w in words if w not in stop_words and len(w) > 3]


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    # Clean up whitespace
    text = ' '.join(text.split())

    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

    return [s.strip() for s in sentences if s.strip()]


def _score_sentence(sentence: str, query_terms: set[str]) -> float:
    """Score a sentence based on query term matches."""
    sentence_lower = sentence.lower()
    sentence_words = set(re.findall(r'\b[a-z]+\b', sentence_lower))

    # Count query term matches
    matches = len(query_terms & sentence_words)

    # Bonus for sentences with military/doctrine indicators
    doctrine_terms = {
        'shall', 'must', 'should', 'commander', 'unit', 'operations',
        'mission', 'task', 'responsibility', 'procedure', 'guidance',
        'doctrine', 'policy', 'regulation', 'echelon', 'platoon',
        'company', 'battalion', 'brigade'
    }
    doctrine_matches = len(doctrine_terms & sentence_words)

    # Penalize very long sentences
    length_penalty = max(0, (len(sentence.split()) - 40) * 0.01)

    score = matches + (doctrine_matches * 0.5) - length_penalty

    return score
