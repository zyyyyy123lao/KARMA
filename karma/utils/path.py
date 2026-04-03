"""Path utilities for KARMA.

Centralizes all path construction and resolution.
"""

import os
from pathlib import Path
from typing import Union


def get_project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent.parent


def resolve_path(relative: Union[str, Path], base: Union[str, Path, None] = None) -> Path:
    """Resolve a relative path to an absolute path.

    If base is not provided, uses the project root as base.
    Supports both absolute and relative paths.
    """
    path = Path(relative)
    if path.is_absolute():
        return path
    base_path = Path(base) if base else get_project_root()
    return base_path / path


class PathResolver:
    """Centralized path resolver for KARMA data directories."""

    def __init__(self, base_path: Union[str, Path, None] = None):
        self._base = resolve_path(base_path or os.environ.get("KARMA_BASE_PATH", "/root/autodl-tmp/KARMA"))

    @property
    def base(self) -> Path:
        return self._base

    @property
    def memory(self) -> Path:
        return self._base / "memory"

    @property
    def short_term_memory(self) -> Path:
        return self.memory / "short_term"

    @property
    def long_term_memory(self) -> Path:
        return self.memory / "longterm_memory.json"

    @property
    def objects_locations(self) -> Path:
        return self.memory / "objects_locations.json"

    @property
    def objects_locations1(self) -> Path:
        return self.memory / "objects_locations1.json"

    @property
    def objects_locations2(self) -> Path:
        return self.memory / "objects_locations2.json"

    @property
    def memory3(self) -> Path:
        return self.memory / "memory3.json"

    @property
    def analysis_results(self) -> Path:
        return self.memory / "analysis_results.json"

    @property
    def logs(self) -> Path:
        return self._base / "logs"

    @property
    def task_description(self) -> Path:
        return self.logs / "task_description.json"

    @property
    def similarity_flag(self) -> Path:
        return self.logs / "similarity_flag.json"

    @property
    def messages(self) -> Path:
        return self.logs / "messages.json"

    @property
    def generated_function_name(self) -> Path:
        return self.logs / "generated_function_name.json"

    @property
    def prompts(self) -> Path:
        return self._base / "prompts"

    @property
    def skills(self) -> Path:
        return self.prompts / "skills.txt"

    @property
    def role(self) -> Path:
        return self.prompts / "role.txt"

    @property
    def instruction(self) -> Path:
        return self.prompts / "instruction.txt"

    @property
    def short_term_memory_prompt(self) -> Path:
        return self.prompts / "short_term_memory.txt"

    @property
    def long_term_memory_prompt(self) -> Path:
        return self.prompts / "long_term_memory.txt"

    @property
    def examples(self) -> Path:
        return self.prompts / "examples.txt"

    @property
    def emphasize(self) -> Path:
        return self.prompts / "emphasize.txt"

    @property
    def experience(self) -> Path:
        return self._base / "experience"

    @property
    def experience_data(self) -> Path:
        return self.experience / "experience.json"

    @property
    def alfred(self) -> Path:
        return self._base / "ALFRED_L"

    @property
    def resources(self) -> Path:
        return self._base / "resources"

    @property
    def history_tasks(self) -> Path:
        return self._base / "history_tasks"

    @property
    def task_history(self) -> Path:
        return self.history_tasks / "task_history.json"

    @property
    def outputs(self) -> Path:
        out = self._base / "data" / "outputs"
        out.mkdir(parents=True, exist_ok=True)
        return out

    @property
    def videos(self) -> Path:
        vid = self._base / "data" / "videos"
        vid.mkdir(parents=True, exist_ok=True)
        return vid

    def agent_folder(self, agent_id: int = 1) -> Path:
        """Return the output folder path for a specific agent."""
        folder = self._base / f"agent_{agent_id}"
        folder.mkdir(exist_ok=True)
        return folder

    @property
    def top_view(self) -> Path:
        folder = self._base / "top_view"
        folder.mkdir(exist_ok=True)
        return folder
