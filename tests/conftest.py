"""Pytest configuration for KARMA tests."""

import os
import sys
from pathlib import Path

# Ensure the project root is on the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """Configure test environment."""
    # Set environment variables for testing
    os.environ.setdefault("KARMA_BASE_PATH", str(project_root))
    os.environ.setdefault("KARMA_LOG_LEVEL", "DEBUG")
