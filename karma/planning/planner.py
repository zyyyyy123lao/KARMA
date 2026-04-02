"""LLM Planner for KARMA.

Provides the high-level planning interface that coordinates
task decomposition and execution.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from karma.config import APIConfig, Config
from karma.planning.task_decomposer import TaskDecomposer
from karma.planning.executor import TaskExecutor
from karma.planning.registry import TaskFunctionRegistry

logger = logging.getLogger("karma.planning.planner")


class LLMPlanner:
    """High-level LLM-based planner for KARMA.

    Combines task decomposition (LLM generation) with execution,
    managing the full pipeline from task description to robot action.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        decomposer: Optional[TaskDecomposer] = None,
        executor: Optional[TaskExecutor] = None,
    ):
        self.config = config or Config.get_instance()
        self.decomposer = decomposer or TaskDecomposer(self.config.api)
        self.executor = executor or TaskExecutor()
        self.registry = self.executor.registry

    def plan_and_execute(
        self,
        task_description: str,
        robot: Any,
        output_file: Optional[str | Path] = None,
    ) -> bool:
        """Full pipeline: decompose task, save code, execute.

        Args:
            task_description: The natural language task.
            robot: Robot instance for execution.
            output_file: Path to task_functions.py for generated code.

        Returns:
            True if execution succeeded.
        """
        if output_file is None:
            output_file = Path(self.config.paths.base) / "scripts" / "task_functions.py"

        # Write task description
        task_file = self.config.paths.task_description
        task_file.parent.mkdir(parents=True, exist_ok=True)
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump({"task_description": task_description}, f, indent=2)

        # Decompose task
        raw_code = self.decomposer.decompose(
            task_description, self.config.paths
        )
        if not raw_code:
            logger.error("Task decomposition returned empty code")
            return False

        # Save generated code
        func_name = self.decomposer.save_generated_code(
            raw_code, output_file
        )
        if func_name is None:
            logger.error("Failed to save generated code")
            return False

        # Execute
        return self.executor.execute_from_file(
            self.config.paths.generated_function_name,
            robot,
        )

    def decompose_only(
        self,
        task_description: str,
    ) -> str:
        """Decompose a task and return the generated code without executing.

        Returns:
            The generated Python code string.
        """
        return self.decomposer.decompose(
            task_description, self.config.paths
        )

    def execute_generated(
        self,
        function_name_file: str | Path,
        robot: Any,
    ) -> bool:
        """Execute a previously generated task function.

        Args:
            function_name_file: Path to generated_function_name.json.
            robot: Robot instance.

        Returns:
            True on success.
        """
        return self.executor.execute_from_file(function_name_file, robot)
