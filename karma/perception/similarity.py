"""Similarity computation for KARMA.

Provides text similarity using sentence embeddings and
task similarity matching for the memory system.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("karma.perception.similarity")


class SimilarityEngine:
    """Computes semantic similarity for KARMA memory queries.

    Wraps sentence-transformers for object and task similarity searches.
    """

    def __init__(self, model_name: str = "all-mpnet-base-v2"):
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        """Lazy-load the embedding model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            logger.info("Loaded similarity model: %s", self.model_name)
        return self._model

    def encode_texts(self, texts: List[str]) -> np.ndarray:
        """Encode a list of texts into embedding vectors."""
        model = self._get_model()
        return model.encode(texts, convert_to_tensor=False)

    def compute_similarity(
        self,
        query: str,
        candidates: List[str],
    ) -> np.ndarray:
        """Compute cosine similarity between a query and a list of candidates.

        Returns:
            Array of similarity scores, one per candidate.
        """
        model = self._get_model()
        query_emb = model.encode(query, convert_to_tensor=False)
        candidate_embs = model.encode(candidates, convert_to_tensor=False)

        # Normalize for cosine similarity
        query_emb = query_emb / np.linalg.norm(query_emb)
        candidate_embs = candidate_embs / np.linalg.norm(candidate_embs, axis=1, keepdims=True)

        return np.dot(candidate_embs, query_emb)

    def find_top_k(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 3,
    ) -> List[Tuple[int, str, float]]:
        """Find the top-k most similar candidates to a query.

        Returns:
            List of (index, candidate, score) tuples sorted by score descending.
        """
        if not candidates:
            return []

        scores = self.compute_similarity(query, candidates)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(int(i), candidates[i], float(scores[i])) for i in top_indices]


def extract_task_from_description(description: str) -> Optional[str]:
    """Extract the actionable task from a full instruction description.

    E.g. "Task 1: Wash the Apple" -> "Wash the Apple"
    """
    colon_idx = description.find(":")
    if colon_idx != -1:
        task = description[colon_idx + 1:].split(".")[0].strip()
        return task if task else None
    return None


def load_experience_json(file_path: str | Path) -> List[Dict[str, Any]]:
    """Load experience data from a JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_task_history(file_path: str | Path) -> List[str]:
    """Load task history from a JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
