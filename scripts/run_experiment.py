"""Experiment runner for KARMA.

Runs multiple experiments from YAML configuration files,
collecting metrics and producing comparison summaries.
"""

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List

from karma import __version__
from karma.config import Config
from karma.agents import AI2ThorController, Robot
from karma.memory import MemoryManager
from karma.planning import LLMPlanner
from karma.utils.logger import ExperimentLogger, setup_logging


def load_experiment_config(config_dir: Path) -> List[Dict[str, Any]]:
    """Load all YAML experiment configurations from a directory."""
    import yaml

    configs = []
    for yaml_file in sorted(config_dir.glob("experiment/*.yaml")):
        with open(yaml_file, "r") as f:
            configs.append(yaml.safe_load(f))
    return configs


def run_single_experiment(
    exp_config: Dict[str, Any],
    base_config: Config,
) -> Dict[str, Any]:
    """Run a single experiment configuration.

    Returns a dict of metrics for the experiment.
    """
    logger = logging.getLogger("karma.experiment")
    exp_type = exp_config.get("experiment", {}).get("type", "unknown")
    task = exp_config.get("experiment", {}).get("task", "unknown")
    scene = exp_config.get("agent", {}).get("scene", "FloorPlan1")

    exp_name = f"exp_{exp_type}_{int(time.time())}"
    logger.info("Running experiment: %s (%s)", exp_name, task)

    # Override scene
    base_config.agent.scene = scene

    results = {
        "experiment": exp_name,
        "task": task,
        "scene": scene,
        "success": False,
        "elapsed_time": 0.0,
        "error": None,
    }

    start_time = time.time()

    try:
        controller = AI2ThorController(base_config.agent)
        controller.initialize()
        robot = Robot(controller, name=base_config.agent.name)
        memory = MemoryManager()
        memory.build_long_term(controller)

        with ExperimentLogger(exp_name, base_config.paths.logs, tags={
            "task": task,
            "scene": scene,
            "type": exp_type,
        }) as exp_logger:
            robot.set_logger(exp_logger)

            planner = LLMPlanner(base_config)
            planner.plan_and_execute(task, robot)

        controller.close()
        results["success"] = True

    except Exception as e:
        logger.error("Experiment failed: %s", e)
        results["error"] = str(e)

    results["elapsed_time"] = time.time() - start_time
    return results


def run_experiments(
    configs: List[Dict[str, Any]],
    base_config: Config,
    output_dir: Path,
) -> List[Dict[str, Any]]:
    """Run a batch of experiments and save results."""
    results = []
    for cfg in configs:
        result = run_single_experiment(cfg, base_config)
        results.append(result)

    # Save results
    output_dir.mkdir(parents=True, exist_ok=True)
    results_file = output_dir / f"experiments_{int(time.time())}.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    return results


def print_summary(results: List[Dict[str, Any]]) -> None:
    """Print a formatted summary of experiment results."""
    print("\n" + "=" * 60)
    print("EXPERIMENT SUMMARY")
    print("=" * 60)
    print(f"{'Experiment':<30} {'Status':<10} {'Time (s)':<12}")
    print("-" * 60)
    for r in results:
        status = "SUCCESS" if r["success"] else "FAILED"
        print(f"{r['experiment']:<30} {status:<10} {r['elapsed_time']:<12.2f}")
    print("-" * 60)
    total = len(results)
    successes = sum(1 for r in results if r["success"])
    print(f"Total: {total}, Success: {successes}, Rate: {successes/total*100:.1f}%")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Run KARMA experiments")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/default.yaml",
        help="Base configuration file",
    )
    parser.add_argument(
        "--experiments",
        type=str,
        default="configs/experiment",
        help="Directory containing experiment YAML files",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/experiments",
        help="Output directory for results",
    )
    args = parser.parse_args()

    # Setup
    config = Config.get_instance(args.config)
    config.ensure_directories()
    setup_logging(config)
    logger = logging.getLogger("karma.experiment")
    logger.info("KARMA v%s experiment runner", __version__)

    # Load experiments
    configs = load_experiment_config(Path(args.experiments))
    logger.info("Loaded %d experiment configurations", len(configs))

    # Run
    results = run_experiments(configs, config, Path(args.output))

    # Print summary
    print_summary(results)


if __name__ == "__main__":
    main()
