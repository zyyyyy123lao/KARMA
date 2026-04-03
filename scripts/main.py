"""Main entry point for KARMA.

Usage:
    python -m scripts.main --task "wash the apple"
    python -m scripts.main --config configs/default.yaml
    python -m scripts.main --gui
"""

import os

# Remove proxy env vars so API calls go direct
for _k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
    os.environ.pop(_k, None)

import argparse
import logging
import sys
from pathlib import Path

from karma import __version__
from karma.config import Config
from karma.utils.logger import setup_logging


def parse_args():
    parser = argparse.ArgumentParser(
        description="KARMA - Embodied AI Agent with Long-and-short Term Memory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--task", "-t",
        type=str,
        default=None,
        help="Task description to execute",
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Path to YAML config file",
    )
    parser.add_argument(
        "--gui", "-g",
        action="store_true",
        help="Launch the GUI instead of CLI mode",
    )
    parser.add_argument(
        "--scene",
        type=str,
        default=None,
        help="Override scene (e.g., FloorPlan1)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"KARMA {__version__}",
    )
    return parser.parse_args()


def run_task(task: str, config: Config) -> None:
    """Run a single task in CLI mode."""
    from karma.agents import AI2ThorController, Robot
    from karma.planning import LLMPlanner
    from karma.memory import MemoryManager
    from karma.utils.logger import ExperimentLogger

    logger = logging.getLogger("karma.main")
    logger.info("Starting KARMA with task: %s", task)

    # Initialize controller and robot
    controller = AI2ThorController(config.agent)
    controller.initialize()

    # Initialize robot
    robot = Robot(controller, name=config.agent.name)

    # Initialize memory
    memory = MemoryManager()
    memory.build_long_term(controller)

    # Setup experiment logger
    experiment_name = f"task_{Path(task).name[:50]}"
    with ExperimentLogger(experiment_name, config.paths.logs, tags={"task": task}) as exp_logger:
        robot.set_logger(exp_logger)

        # Initialize and run planner
        planner = LLMPlanner(config)
        planner.plan_and_execute(task, robot)

    controller.close()
    logger.info("Task completed: %s", task)


def run_gui(config: Config) -> None:
    """Launch the GUI application."""
    from karma.gui import KARMAApp
    app = KARMAApp(config)
    app.run()


def main():
    args = parse_args()

    # Load configuration
    config_path = str(Path(__file__).parent.parent / "configs" / "default.yaml")
    api_path = str(Path(__file__).parent.parent / "configs" / "api.yaml")

    # Merge default + api overrides into a single dict before loading
    import yaml
    from karma.config import _resolve_dict_env_vars
    merged = {}
    for p in [config_path, api_path]:
        if Path(p).exists():
            with open(p) as f:
                part = yaml.safe_load(f)
            if part:
                for k, v in part.items():
                    if isinstance(v, dict) and k in merged:
                        merged[k].update(v)
                    else:
                        merged[k] = v
    merged = _resolve_dict_env_vars(merged)

    config = Config.get_instance()
    base_path = Path("/root/autodl-tmp/KARMA")
    from karma.config import APIConfig, AgentConfig, MemoryConfig, PathConfig, LoggingConfig
    if "api" in merged:
        config.api = APIConfig.from_dict(merged.get("api", {}))
    if "agent" in merged:
        config.agent = AgentConfig.from_dict(merged)
    if "memory" in merged:
        config.memory = MemoryConfig.from_dict(merged)
    if "paths" in merged:
        config.paths = PathConfig.from_dict(base_path, merged)
    if "logging" in merged:
        config.logging = LoggingConfig.from_dict(merged)

    # Override scene if provided
    if args.scene:
        config.agent.scene = args.scene

    # Override log level
    if args.verbose:
        config.logging.level = "DEBUG"

    # Setup logging
    config.ensure_directories()
    setup_logging(config)

    logger = logging.getLogger("karma.main")
    logger.info("KARMA v%s starting...", __version__)

    # Launch GUI or CLI
    if args.gui or args.task is None:
        run_gui(config)
    else:
        run_task(args.task, config)


if __name__ == "__main__":
    main()
