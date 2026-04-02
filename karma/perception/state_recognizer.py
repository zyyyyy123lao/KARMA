"""Object state recognition utilities for KARMA."""

from typing import Dict, List


VALID_STATES = [
    "heated", "cooked", "sliced", "cleaned", "dirty",
    "filled", "used up", "off", "on", "opened", "closed", "none",
]


def is_valid_state(state: str) -> bool:
    """Check if a state string is a recognized valid state."""
    return state.lower() in VALID_STATES


def normalize_state(state: str) -> str:
    """Normalize a state string to lowercase."""
    return state.lower().strip()


class StateRecognizer:
    """Recognizes object states from natural language descriptions.

    Maps raw LLM output descriptions to structured state values.
    """

    def __init__(self):
        self._valid_states = set(s.lower() for s in VALID_STATES)

    def recognize(self, raw_text: str) -> Dict[str, str]:
        """Parse state descriptions from raw text.

        Args:
            raw_text: Raw LLM output like "Apple: cleaned\nTomato: sliced"

        Returns:
            Dict of {object_name: normalized_state}
        """
        result = {}
        for line in raw_text.split("\n"):
            if ": " in line:
                parts = line.split(": ", 1)
                if len(parts) == 2:
                    obj = parts[0].strip()
                    state = self.normalize(parts[1].strip())
                    if self.is_valid(state):
                        result[obj] = state
        return result

    def is_valid(self, state: str) -> bool:
        """Check if state is in the valid states list."""
        return state.lower() in self._valid_states

    def normalize(self, state: str) -> str:
        """Normalize and return the state string."""
        return state.lower().strip()

    def get_valid_states(self) -> List[str]:
        """Return all valid state strings."""
        return list(self._valid_states)
