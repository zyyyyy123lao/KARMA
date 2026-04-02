"""Perception module for KARMA.

Handles image analysis, state recognition, and semantic similarity
for the embodied agent's perceptual capabilities.
"""

from karma.perception.image_analyzer import ImageAnalyzer, encode_image, encode_frame
from karma.perception.state_recognizer import StateRecognizer, is_valid_state, normalize_state, VALID_STATES
from karma.perception.similarity import (
    SimilarityEngine,
    extract_task_from_description,
    load_experience_json,
    load_task_history,
)

__all__ = [
    "ImageAnalyzer",
    "StateRecognizer",
    "SimilarityEngine",
    "encode_image",
    "encode_frame",
    "is_valid_state",
    "normalize_state",
    "VALID_STATES",
    "extract_task_from_description",
    "load_experience_json",
    "load_task_history",
]
