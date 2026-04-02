"""Debug utilities for KARMA.

Provides a REPL-like debug console and inspection helpers.
"""

import code
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("karma.debug")


def inspect_object_locations(memory_dir: str | Path) -> None:
    """Print all object locations from a memory JSON file."""
    path = Path(memory_dir) / "objects_locations.json"
    if not path.exists():
        logger.error("File not found: %s", path)
        return
    with open(path, "r") as f:
        data = json.load(f)
    print(f"\nObjects in scene ({len(data)} total):")
    print("-" * 60)
    for item in data:
        pos = item["position"]
        print(
            f"  {item['objectType']:<25} "
            f"x={pos['x']:6.2f} y={pos['y']:5.2f} z={pos['z']:6.2f}  "
            f"[{item['objectId']}]"
        )
    print()


def inspect_short_term_memory(memory_dir: str | Path) -> None:
    """Print short-term memory (changed objects)."""
    path = Path(memory_dir) / "memory3.json"
    if not path.exists():
        logger.warning("Short-term memory file not found: %s", path)
        return
    with open(path, "r") as f:
        data = json.load(f)
    print(f"\nShort-term Memory ({len(data)} objects):")
    print("-" * 60)
    for item in data:
        pos = item["position"]
        state = item.get("state", "none")
        print(
            f"  {item['objectType']:<20} "
            f"state={state:<10} "
            f"pos=({pos['x']:.2f}, {pos['y']:.2f}, {pos['z']:.2f})"
        )
    print()


def inspect_long_term_memory(memory_file: str | Path) -> None:
    """Print long-term memory regions."""
    with open(memory_file, "r") as f:
        data = json.load(f)
    print(f"\nLong-term Memory ({len(data)} regions):")
    print("-" * 60)
    for center, objects in data.items():
        types = [o["objectType"] for o in objects]
        print(f"  {center}: {', '.join(types)}")
    print()


def interactive_debug() -> None:
    """Launch an interactive Python debug console with KARMA imports."""
    banner = """
KARMA Debug Console
Available locals: None (import modules as needed)
Example:
    from karma.config import Config
    from karma.agents import AI2ThorController, Robot
    config = Config.get_instance()
    """
    code.interact(banner=banner, local=globals())


if __name__ == "__main__":
    interactive_debug()
