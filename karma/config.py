"""Configuration management for KARMA.

Loads configuration from YAML files and environment variables.
Provides a singleton Config instance for the entire application.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


def _resolve_env_var(value: Any) -> Any:
    """Resolve environment variable placeholders in config values.

    Supports formats like: ${VAR_NAME} or ${VAR_NAME:-default}
    """
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        inner = value[2:-1]
        if ":-" in inner:
            var_name, default = inner.split(":-", 1)
            return os.environ.get(var_name.strip(), default.strip())
        return os.environ.get(inner.strip(), "")
    return value


def _resolve_dict_env_vars(data: Any) -> Any:
    """Recursively resolve environment variables in a dictionary."""
    if isinstance(data, dict):
        return {k: _resolve_dict_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_resolve_dict_env_vars(item) for item in data]
    return _resolve_env_var(data)


@dataclass
class APIConfig:
    api_key: str = ""
    base_url: str = "https://api.chatanywhere.tech/v1"
    model_name: str = "gpt-4o"
    embedding_model_name: str = "text-embedding-3-large"
    temperature: float = 0.0
    max_tokens: int = 4096

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "APIConfig":
        return cls(
            api_key=_resolve_env_var(data.get("api_key", "")),
            base_url=data.get("base_url", "https://api.chatanywhere.tech/v1"),
            model_name=data.get("model_name", "gpt-4o"),
            embedding_model_name=data.get("embedding_model_name", "text-embedding-3-large"),
            temperature=float(data.get("temperature", 0.0)),
            max_tokens=int(data.get("max_tokens", 4096)),
        )


@dataclass
class AgentConfig:
    name: str = "robot1"
    agent_mode: str = "default"
    visibility_distance: float = 100.0
    grid_size: float = 0.25
    rotate_step_degrees: int = 20
    quality: str = "Low"
    width: int = 900
    height: int = 900
    field_of_view: int = 90
    scene: str = "FloorPlan1"
    agent_count: int = 1
    render_depth_image: bool = False
    render_instance_segmentation: bool = False
    snap_to_grid: bool = False

    # Navigation thresholds
    goal_threshold: float = 0.3
    distance_delta_threshold: float = 0.2
    stuck_count_limit: int = 15
    reachable_threshold: float = 0.3
    explore_exit_distance: float = 1.5

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        nested = data.get("agent", {})
        return cls(
            name=nested.get("name", "robot1"),
            agent_mode=nested.get("agent_mode", "default"),
            visibility_distance=float(nested.get("visibility_distance", 100.0)),
            grid_size=float(nested.get("grid_size", 0.25)),
            rotate_step_degrees=int(nested.get("rotate_step_degrees", 20)),
            quality=nested.get("quality", "Low"),
            width=int(nested.get("width", 900)),
            height=int(nested.get("height", 900)),
            field_of_view=int(nested.get("field_of_view", 90)),
            scene=nested.get("scene", "FloorPlan1"),
            agent_count=int(nested.get("agent_count", 1)),
            render_depth_image=bool(nested.get("render_depth_image", False)),
            render_instance_segmentation=bool(nested.get("render_instance_segmentation", False)),
            snap_to_grid=bool(nested.get("snap_to_grid", False)),
            goal_threshold=float(nested.get("goal_threshold", 0.3)),
            distance_delta_threshold=float(nested.get("distance_delta_threshold", 0.2)),
            stuck_count_limit=int(nested.get("stuck_count_limit", 15)),
            reachable_threshold=float(nested.get("reachable_threshold", 0.3)),
            explore_exit_distance=float(nested.get("explore_exit_distance", 1.5)),
        )


@dataclass
class MemoryConfig:
    short_term_max_size: int = 100
    similarity_threshold: float = 0.3
    position_change_threshold: float = 0.3
    short_term_recall_top_k: int = 3
    long_term_max_areas: int = 3
    embedding_model: str = "text-embedding-3-large"
    exploration_positions: List[List[float]] = field(default_factory=lambda: [
        [1.25, 0.0, -1.75], [-1.0, 0.0, 0.0], [-0.25, 0.0, -1.5],
        [-1.0, 0.0, -1.5], [0.5, 0.0, 1.5], [1.5, 0.0, -0.25],
        [1.5, 0.0, 1.0], [-2.0, 0.0, 2.0],
    ])

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryConfig":
        nested = data.get("memory", {})
        positions = nested.get("exploration_positions", None)
        return cls(
            short_term_max_size=int(nested.get("short_term_max_size", 100)),
            similarity_threshold=float(nested.get("similarity_threshold", 0.3)),
            position_change_threshold=float(nested.get("position_change_threshold", 0.3)),
            short_term_recall_top_k=int(nested.get("short_term_recall_top_k", 3)),
            long_term_max_areas=int(nested.get("long_term_max_areas", 3)),
            embedding_model=nested.get("embedding_model", "text-embedding-3-large"),
            exploration_positions=positions if positions else cls().exploration_positions,
        )


@dataclass
class PathConfig:
    base: Path = field(default_factory=lambda: Path("/root/autodl-tmp/KARMA"))
    memory: Path = field(default_factory=lambda: Path("data/memory"))
    logs: Path = field(default_factory=lambda: Path("data/logs"))
    outputs: Path = field(default_factory=lambda: Path("data/outputs"))
    videos: Path = field(default_factory=lambda: Path("data/videos"))
    prompts: Path = field(default_factory=lambda: Path("prompts"))
    experience: Path = field(default_factory=lambda: Path("experience"))
    alfred: Path = field(default_factory=lambda: Path("ALFRED_L"))
    history_tasks: Path = field(default_factory=lambda: Path("history_tasks"))
    memory3: Path = field(default_factory=lambda: Path("memory/memory3.json"))
    task_history: Path = field(default_factory=lambda: Path("history_tasks/task_history.json"))
    task_description: Path = field(default_factory=lambda: Path("logs/task_description.json"))
    similarity_flag: Path = field(default_factory=lambda: Path("logs/similarity_flag.json"))
    generated_function_name: Path = field(default_factory=lambda: Path("logs/generated_function_name.json"))
    messages: Path = field(default_factory=lambda: Path("logs/messages.json"))

    @classmethod
    def from_dict(cls, base_path: Path, data: Dict[str, Any]) -> "PathConfig":
        nested = data.get("paths", {})
        return cls(
            base=base_path,
            memory=base_path / nested.get("memory", "data/memory"),
            logs=base_path / nested.get("logs", "data/logs"),
            outputs=base_path / nested.get("outputs", "data/outputs"),
            videos=base_path / nested.get("videos", "data/videos"),
            prompts=base_path / nested.get("prompts", "prompts"),
            experience=base_path / nested.get("experience", "experience"),
            alfred=base_path / nested.get("alfred", "ALFRED_L"),
            history_tasks=base_path / nested.get("history_tasks", "history_tasks"),
            memory3=base_path / nested.get("memory3", "memory/memory3.json"),
            task_history=base_path / nested.get("task_history", "history_tasks/task_history.json"),
            task_description=base_path / nested.get("task_description", "logs/task_description.json"),
            similarity_flag=base_path / nested.get("similarity_flag", "logs/similarity_flag.json"),
            generated_function_name=base_path / nested.get("generated_function_name", "logs/generated_function_name.json"),
            messages=base_path / nested.get("messages", "logs/messages.json"),
        )


@dataclass
class LoggingConfig:
    level: str = "INFO"
    format_str: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None
    console: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LoggingConfig":
        nested = data.get("logging", {})
        return cls(
            level=nested.get("level", "INFO"),
            format_str=nested.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            file=nested.get("file", None),
            console=nested.get("console", True),
        )


class Config:
    """Singleton configuration manager for the KARMA project."""

    _instance: Optional["Config"] = None

    def __init__(self, config_file: Optional[str] = None):
        self.api: APIConfig = APIConfig()
        self.agent: AgentConfig = AgentConfig()
        self.memory: MemoryConfig = MemoryConfig()
        self.paths: PathConfig = PathConfig()
        self.logging: LoggingConfig = LoggingConfig()

        if config_file:
            self.load(config_file)

    @classmethod
    def get_instance(cls, config_file: Optional[str] = None) -> "Config":
        """Get or create the singleton Config instance."""
        if cls._instance is None:
            cls._instance = cls(config_file)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None

    def load(self, config_file: str) -> None:
        """Load configuration from a YAML file."""
        path = Path(config_file)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        data = _resolve_dict_env_vars(data)

        base_path = Path("/root/autodl-tmp/KARMA")

        if "api" in data:
            self.api = APIConfig.from_dict(data)
        if "agent" in data:
            self.agent = AgentConfig.from_dict(data)
        if "memory" in data:
            self.memory = MemoryConfig.from_dict(data)
        if "paths" in data:
            self.paths = PathConfig.from_dict(base_path, data)
        if "logging" in data:
            self.logging = LoggingConfig.from_dict(data)

    def update(self, **kwargs) -> None:
        """Update configuration values dynamically."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def ensure_directories(self) -> None:
        """Ensure all configured directories exist."""
        for attr_name in ["memory", "logs", "outputs", "videos"]:
            path = getattr(self.paths, attr_name, None)
            if path:
                path.mkdir(parents=True, exist_ok=True)
