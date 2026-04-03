"""File utilities for KARMA."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def read_json(file_path: str | Path) -> Any:
    """Read and parse a JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(file_path: str | Path, data: Any, indent: int = 4) -> None:
    """Write data to a JSON file."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def read_text(file_path: str | Path) -> str:
    """Read a text file and return its contents."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def write_text(file_path: str | Path, content: str) -> None:
    """Write content to a text file."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def load_lines(file_path: str | Path) -> List[str]:
    """Read a file and return a list of non-empty lines."""
    return [line.rstrip("\n") for line in open(file_path, "r", encoding="utf-8") if line.strip()]


def insert_into_file(
    file_path: str | Path,
    new_code: str,
    line_number: int,
) -> None:
    """Insert new code into a file at the specified line number (1-indexed)."""
    path = Path(file_path)
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    insert_idx = max(0, line_number - 1)
    before = lines[:insert_idx]
    after = lines[insert_idx:]

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(before)
        f.write(new_code + "\n")
        f.writelines(after)


def append_to_file(file_path: str | Path, content: str) -> None:
    """Append content to a file."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(content + "\n")


def merge_json_files(
    files: List[str | Path],
    output_file: str | Path,
    key_field: str = "objectId",
    max_size: int = 100,
) -> None:
    """Merge multiple JSON files by deduplicating entries by key field.

    If the merged size exceeds max_size, keeps the most recent entries.
    """
    merged: Dict[str, Any] = {}
    for file_path in files:
        try:
            data = read_json(file_path)
            if isinstance(data, list):
                for item in data:
                    key = item.get(key_field)
                    if key:
                        merged[key] = item
        except (FileNotFoundError, json.JSONDecodeError):
            continue

    if len(merged) > max_size:
        sorted_items = sorted(
            merged.items(),
            key=lambda x: x[1].get("timestamp", 0),
            reverse=True,
        )
        merged = dict(sorted_items[:max_size])

    write_json(output_file, list(merged.values()))
