from collections.abc import Sequence

import numpy as np
from huggingface_hub import InferenceClient

from ingestion.config import settings
from ingestion.hash_embed import hash_embed_many


class Embedder:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._use_hf = model_name != "mpost-hash-384"

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        if not self._use_hf:
            return hash_embed_many(texts)

        # Use HuggingFace Inference API for embeddings
        return self._encode_hf(list(texts))

    def _encode_hf(self, texts: list[str]) -> list[list[float]]:
        """Encode texts using HuggingFace Inference API."""
        if not settings.hf_api_token:
            print("Warning: No HF_API_TOKEN found, falling back to hash embeddings")
            return hash_embed_many(texts)

        # Batch API calls (max 100 per request recommended)
        batch_size = 50
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self._encode_batch_hf(batch)
            if batch_embeddings is None:
                print(f"HF embedding failed for batch {i//batch_size + 1}, using hash fallback")
                all_embeddings.extend(hash_embed_many(batch))
            else:
                all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def _encode_batch_hf(self, texts: list[str]) -> list[list[float]] | None:
        """Encode a batch of texts using HuggingFace Inference API."""
        try:
            client = InferenceClient(token=settings.hf_api_token)

            # Use feature_extraction for embeddings
            # Returns a numpy array (single text) or 2D array (multiple texts)
            result = client.feature_extraction(
                text=texts,
                model=self.model_name,
            )

            # Convert numpy array to list
            if isinstance(result, np.ndarray):
                if result.ndim == 1:
                    # Single embedding, wrap in a list
                    return [result.tolist()]
                elif result.ndim == 2:
                    # Multiple embeddings
                    return result.tolist()

            # If it's already a list, check format
            if isinstance(result, list):
                if len(result) > 0 and isinstance(result[0], list):
                    return result
                return [result]

            return None
        except Exception as e:
            print(f"HF Embedding error: {type(e).__name__}: {e}")
            return None
