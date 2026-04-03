"""Image analysis for KARMA.

Analyzes AI2-THOR frames using GPT-4o vision to infer object states.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from karma.config import APIConfig

logger = logging.getLogger("karma.perception.image_analyzer")


ANALYSIS_PROMPT = """As an image analysis expert, your task is to infer the state of objects in the image through step-by-step reasoning.

1. Provide a detailed description of this image.
2. From the given task [Task], extract the relevant content from the first step's image description that pertains to the mentioned objects.
3. Based on the object descriptions extracted in the second step, match each object to one of the following states: heated, cooked, sliced, cleaned, dirty, filled, used up, off, on, opened, closed, none.
4. Summarize the results from step three in the following format: object: state. Please only output the content of the last step summary."""


def encode_image(image_path: str | Path) -> str:
    """Encode an image file as a base64 string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def encode_frame(frame) -> str:
    """Encode a NumPy frame as a base64 JPEG string."""
    import cv2
    _, buffer = cv2.imencode(".jpg", cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    return base64.b64encode(buffer).decode("utf-8")


class ImageAnalyzer:
    """Analyzes AI2-THOR frames to infer object states using GPT-4o vision."""

    def __init__(self, api_config: Optional[APIConfig] = None):
        self.api_config = api_config or APIConfig()
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_config.api_key}",
        }

    def analyze_image(
        self,
        image_path: str | Path,
        task: str,
    ) -> Dict[str, Any]:
        """Analyze a single image file.

        Returns:
            The raw API response dict.
        """
        base64_image = encode_image(image_path)
        return self._call_vision(base64_image, task)

    def analyze_frame(
        self,
        frame,
        task: str,
    ) -> Dict[str, Any]:
        """Analyze a NumPy frame array.

        Returns:
            The raw API response dict.
        """
        base64_image = encode_frame(frame)
        return self._call_vision(base64_image, task)

    def _call_vision(self, base64_image: str, task: str) -> Dict[str, Any]:
        """Make the API call to the vision model."""
        payload = {
            "model": self.api_config.model_name,
            "messages": [
                {"role": "system", "content": ANALYSIS_PROMPT},
                {"role": "user", "content": f"[Task]: {task}"},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ],
                },
            ],
            "max_tokens": self.api_config.max_tokens,
        }

        try:
            response = requests.post(
                f"{self.api_config.base_url}/chat/completions",
                headers=self._headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error("Image analysis API call failed: %s", e)
            return {}

    def parse_states(self, response: Dict[str, Any]) -> Dict[str, str]:
        """Parse the API response into a dict of {object: state}.

        Args:
            response: Raw API response from analyze_image/analyze_frame.

        Returns:
            Dict mapping object names to state strings.
        """
        try:
            content = (
                response.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
        except (IndexError, AttributeError):
            return {}

        states = {}
        for line in content.split("\n"):
            if ": " in line:
                parts = line.split(": ", 1)
                if len(parts) == 2:
                    obj, state = parts
                    states[obj.strip()] = state.strip()
        return states

    def analyze_and_parse(
        self,
        image_path: str | Path,
        task: str,
    ) -> Dict[str, str]:
        """Convenience: analyze and return parsed state dict."""
        response = self.analyze_image(image_path, task)
        return self.parse_states(response)

    def update_memory_with_states(
        self,
        memory_file: str | Path,
        analysis_file: str | Path,
    ) -> None:
        """Update a memory JSON file with object states from analysis results.

        Args:
            memory_file: Path to memory3.json (object list).
            analysis_file: Path to analysis_results.json.
        """
        import json

        with open(memory_file, "r", encoding="utf-8") as f:
            memory_data = json.load(f)

        with open(analysis_file, "r", encoding="utf-8") as f:
            analysis_data = json.load(f)

        # Get the latest analysis entry
        last_key = list(analysis_data.keys())[-1]
        state_data = {
            obj.lower(): state
            for obj, state in analysis_data[last_key].items()
        }

        for item in memory_data:
            obj_type = item.get("objectType", "").lower()
            if obj_type in state_data:
                item["state"] = state_data[obj_type]

        with open(memory_file, "w", encoding="utf-8") as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=4)
