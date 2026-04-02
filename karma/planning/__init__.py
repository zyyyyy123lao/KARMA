"""Planning module for KARMA.

Handles task decomposition, LLM-based planning, and task execution.
  - TaskDecomposer: breaks tasks into Python code via LLM
  - LLMPlanner: high-level planning interface
  - TaskExecutor: background task queue executor
  - TaskFunctionRegistry: dynamic function management

Lazy imports to avoid hard dependency on openai at import time.
"""

_SUBMODULES = {
    "TaskDecomposer": "task_decomposer",
    "LLMPlanner": "planner",
    "TaskExecutor": "executor",
    "TaskFunctionRegistry": "registry",
}
_loaded = {}


def __getattr__(name: str):
    if name not in _SUBMODULES:
        raise AttributeError(f"module 'karma.planning' has no attribute '{name}'")
    if name not in _loaded:
        import importlib
        mod_name = _SUBMODULES[name]
        mod = importlib.import_module(f"karma.planning.{mod_name}")
        _loaded[name] = getattr(mod, name)
    return _loaded[name]


def __dir__():
    return list(_SUBMODULES.keys())