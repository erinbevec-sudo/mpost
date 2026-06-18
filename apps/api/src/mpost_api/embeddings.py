from functools import lru_cache

import numpy as np
from huggingface_hub import InferenceClient

from mpost_api.config import settings
from mpost_api.hash_embed import hash_embed


class QueryEmbedder:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._use_hf = model_name != "mpost-hash-384"

    def encode_one(self, text: str) -> list[float]:
        if not self._use_hf:
            return hash_embed(text)

        # Use HuggingFace for query embeddings
        embedding = self._encode_hf(text)
        return embedding if embedding is not None else hash_embed(text)

    def _encode_hf(self, text: str) -> list[float] | None:
        """Encode text using HuggingFace Inference API."""
        if not settings.hf_api_token:
            return None

        try:
            client = InferenceClient(token=settings.hf_api_token)

            # Use feature_extraction for embeddings
            result = client.feature_extraction(
                text=text,
                model=self.model_name,
            )

            # Convert numpy array to list
            if isinstance(result, np.ndarray):
                return result.tolist()

            # If it's already a list, return it
            if isinstance(result, list):
                if len(result) > 0 and isinstance(result[0], (int, float)):
                    return result
                # If it's 2D, take first embedding
                elif len(result) > 0 and isinstance(result[0], list):
                    return result[0]

            return None
        except Exception as e:
            print(f"Query embedding error: {type(e).__name__}: {e}")
            return None


@lru_cache(maxsize=1)
def get_query_embedder() -> QueryEmbedder:
    return QueryEmbedder(settings.embedding_model)


def format_vector(embedding: list[float]) -> str:
    return "[" + ",".join(str(value) for value in embedding) + "]"
