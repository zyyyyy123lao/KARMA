"""Logging utilities for KARMA.

Provides structured logging with configurable levels, file output, and experiment tracking.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from karma.config import Config


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for development readability."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(config: Config) -> logging.Logger:
    """Configure the root logger from Config settings."""
    logger = logging.getLogger("karma")
    logger.setLevel(getattr(logging, config.logging.level.upper(), logging.INFO))
    logger.handlers.clear()

    fmt = logging.Formatter(config.logging.format_str)

    if config.logging.console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(ColoredFormatter(config.logging.format_str))
        logger.addHandler(console_handler)

    if config.logging.file:
        file_path = config.paths.logs / config.logging.file
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.

    Usage:
        logger = get_logger(__name__)
        logger.info("Starting experiment", extra={"task": "wash_apple"})
    """
    return logging.getLogger(f"karma.{name}")


@dataclass
class MetricRecord:
    """A single metric measurement."""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)


class ExperimentLogger:
    """Structured experiment logger for tracking runs, metrics, and actions."""

    def __init__(
        self,
        experiment_name: str,
        log_dir: Path,
        tags: Optional[Dict[str, str]] = None,
    ):
        self.experiment_name = experiment_name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.tags = tags or {}
        self.metrics: List[MetricRecord] = []
        self.actions: List[Dict[str, Any]] = []
        self.start_time = time.time()

        self.metrics_file = self.log_dir / f"{experiment_name}_metrics.jsonl"
        self.actions_file = self.log_dir / f"{experiment_name}_actions.jsonl"

        self.logger = get_logger("experiment")
        self.logger.info(
            f"Experiment started: {experiment_name}",
            extra={"tags": self.tags},
        )

    def log_metric(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Log a named metric value."""
        record = MetricRecord(
            name=name,
            value=value,
            tags={**self.tags, **(tags or {})},
        )
        self.metrics.append(record)
        with open(self.metrics_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.__dict__, ensure_ascii=False) + "\n")

    def log_action(
        self,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        success: bool = True,
        duration: Optional[float] = None,
    ) -> None:
        """Log an action execution with its parameters and outcome."""
        entry = {
            "action": action,
            "params": params or {},
            "result": result or {},
            "success": success,
            "duration": duration,
            "timestamp": time.time(),
            "elapsed": time.time() - self.start_time,
            "tags": self.tags,
        }
        self.actions.append(entry)
        with open(self.actions_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def log_navigation(
        self,
        from_pos: Dict[str, float],
        to_pos: Dict[str, float],
        target_object: str,
        steps: int,
        success: bool,
    ) -> None:
        """Log a navigation event."""
        self.log_action(
            action="navigation",
            params={
                "from": from_pos,
                "to": to_pos,
                "target_object": target_object,
                "steps": steps,
            },
            result={"success": success},
            success=success,
        )

    def save_summary(self, output_path: Optional[Path] = None) -> None:
        """Save an experiment summary JSON file."""
        elapsed = time.time() - self.start_time

        total_actions = len(self.actions)
        successful_actions = sum(1 for a in self.actions if a["success"])
        failed_actions = total_actions - successful_actions

        summary = {
            "experiment_name": self.experiment_name,
            "tags": self.tags,
            "elapsed_time_seconds": elapsed,
            "total_actions": total_actions,
            "successful_actions": successful_actions,
            "failed_actions": failed_actions,
            "success_rate": (
                successful_actions / total_actions if total_actions > 0 else 0.0
            ),
            "metrics": {
                r.name: {"values": [], "tags": r.tags}
                for r in self.metrics
            },
        }

        for r in self.metrics:
            summary["metrics"][r.name]["values"].append({
                "value": r.value,
                "timestamp": r.timestamp,
            })

        path = output_path or (self.log_dir / f"{self.experiment_name}_summary.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        self.logger.info(
            f"Experiment finished: {self.experiment_name}",
            extra={
                "summary": {
                    "elapsed": elapsed,
                    "success_rate": summary["success_rate"],
                }
            },
        )

    def __enter__(self) -> "ExperimentLogger":
        return self

    def __exit__(self, *args) -> None:
        self.save_summary()
