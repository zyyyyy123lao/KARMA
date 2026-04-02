"""Task executor for KARMA.

Orchestrates the full task execution pipeline:
loading a generated function, parsing task descriptions,
and running the task with a robot agent.
"""

import json
import logging
import queue
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("karma.planning.executor")


class TaskExecutor:
    """High-level task execution engine.

    Manages a task queue, executes LLM-generated task functions
    on a robot, and coordinates with the action executor.
    """

    def __init__(self, registry: Optional[Any] = None):
        self.registry = registry
        self._task_queue: queue.Queue = queue.Queue()
        self._executor_thread: Optional[threading.Thread] = None
        self._running = False

    @property
    def _registry(self):
        if self.registry is None:
            from karma.planning.registry import TaskFunctionRegistry
            self.registry = TaskFunctionRegistry()
        return self.registry

    def add_task(self, function_name: str, robot: Any) -> None:
        """Add a task to the execution queue.

        Args:
            function_name: Name of the task function.
            robot: Robot instance to execute the task.
        """
        self._task_queue.put({"function_name": function_name, "robot": robot})

    def load_task_from_file(self, file_path: str | Path) -> Optional[str]:
        """Load the generated function name from a JSON file.

        Returns:
            The function name string, or None.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("function_name")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error("Failed to load function name: %s", e)
            return None

    def execute_from_file(
        self,
        function_name_file: str | Path,
        robot: Any,
    ) -> bool:
        """Load function name from file and execute it.

        Args:
            function_name_file: Path to generated_function_name.json.
            robot: Robot instance.

        Returns:
            True on success.
        """
        func_name = self.load_task_from_file(function_name_file)
        if func_name is None:
            logger.error("No function name found in file")
            return False

        self._registry.reload()
        return self._registry.execute(func_name, robot)

    def start_background(self) -> None:
        """Start the background task executor thread."""
        if self._running:
            logger.warning("Task executor already running")
            return
        self._running = True
        self._executor_thread = threading.Thread(
            target=self._run_loop,
            args=(self._task_queue,),
            daemon=True,
        )
        self._executor_thread.start()
        logger.info("Task executor started")

    def stop(self) -> None:
        """Stop the background executor and wait for completion."""
        self._running = False
        self._task_queue.put(None)
        if self._executor_thread:
            self._executor_thread.join(timeout=5.0)
        logger.info("Task executor stopped")

    def _run_loop(self, q: queue.Queue) -> None:
        """Background loop that processes tasks from the queue."""
        while self._running:
            try:
                task = q.get(timeout=1.0)
                if task is None:
                    break
                func_name = task["function_name"]
                robot = task["robot"]
                self._registry.reload()
                self._registry.execute(func_name, robot)
                q.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error("Task execution error: %s", e)