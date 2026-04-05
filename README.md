# KARMA - Embodied AI Agent with Memory Systems

> Augmenting Embodied AI Agents with Long-and-short Term Memory Systems

KARMA is a research-grade embodied AI agent that uses a three-tier memory system (short-term, long-term, semantic) combined with GPT-4o task planning to complete complex household tasks in the AI2-THOR simulation environment.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Running](#running)
- [Configuration](#configuration)
- [Refactoring](#refactoring)
---

## Quick Start

### 1. Environment Setup

```bash
# Create Conda environment
conda env create -f environment.yml
conda activate karma

# Or install with pip
pip install -e .
```

### 2. Set API Key

```bash
# Method 1: environment variable (recommended)
export OPENAI_API_KEY="your-api-key-here"

# Method 2: write directly to config (local dev only)
# Edit configs/api.yaml
```

### 3. Run a Task

```bash
# CLI mode: execute a single task
python -m scripts.main --task "wash the apple"

# Specify scene
python -m scripts.main --task "slice the tomato" --scene FloorPlan2

# Use a config file
python -m scripts.main --config configs/experiment/complex.yaml --verbose

# GUI mode: launch graphical interface
python -m scripts.main --gui

# Batch experiments
python -m scripts.run_experiment --experiments configs/experiment
```

---

## Project Structure

```
KARMA/
├── karma/                          # Core code package
│   ├── __init__.py               # Package init, version info
│   ├── __version__.py            # Version number
│   ├── config.py                 # Singleton configuration manager
│   ├── constants.py               # Global constants (magic numbers centralized)
│   │
│   ├── agents/                    # Agent module
│   │   ├── robot.py              # Robot class (unified interface)
│   │   ├── controller.py         # AI2-THOR controller wrapper
│   │   ├── navigation.py         # Navigation system (GoToObject, Explore...)
│   │   ├── skills.py             # Skill base class + skill registry
│   │   └── action_executor.py    # Background action execution engine
│   │
│   ├── memory/                    # Memory system
│   │   ├── base.py                # Memory abstract base class, ObjectRecord
│   │   ├── short_term.py          # Short-term memory (multi-modal vector cache)
│   │   ├── long_term.py           # Long-term memory (3D Scene Graph 3DSG)
│   │   ├── semantic.py             # Semantic memory (experience retrieval)
│   │   └── manager.py             # Unified memory manager
│   │
│   ├── perception/                # Perception module
│   │   ├── image_analyzer.py      # Image analysis (GPT-4o multi-modal)
│   │   ├── state_recognizer.py    # Object state recognition
│   │   └── similarity.py          # Similarity computation engine
│   │
│   ├── planning/                  # Planning module
│   │   ├── task_decomposer.py     # Task decomposition (LLM generates Python code)
│   │   ├── planner.py             # LLM planner (high-level interface)
│   │   ├── executor.py            # Task executor (background run)
│   │   └── registry.py           # Task function registry
│   │
│   ├── utils/                     # Utilities
│   │   ├── logger.py              # Structured logging + experiment tracking
│   │   ├── path.py                # Path resolution
│   │   ├── file_utils.py          # File utilities
│   │   └── video.py               # Video generation
│   │
│   └── gui/                       # GUI module
│       └── app.py                 # Tkinter graphical interface
│
├── scripts/                       # Run scripts
│   ├── main.py                    # Main entry point (CLI/GUI unified)
│   ├── run_experiment.py         # Batch experiment runner
│   ├── task_functions.py         # Output location for LLM-generated code
│   ├── debug.py                  # Debugging tools
│   └── action_wrappers.py        # Action wrappers
│
├── configs/                       # Configuration files
│   ├── default.yaml               # Default configuration
│   ├── api.yaml                   # API credentials (sensitive)
│   └── experiment/                # Pre-defined experiment configurations
│       ├── simple.yaml            # Simple tasks
│       ├── complex.yaml           # Complex tasks
│       └── composite.yaml         # Composite tasks
│
├── prompts/                        # Prompt templates
│   ├── skills.txt                 # Skill definitions
│   ├── role.txt                   # Role definition
│   ├── instruction.txt            # Instruction template
│   ├── short_term_memory.txt      # Short-term memory prompts
│   ├── long_term_memory.txt       # Long-term memory prompts
│   ├── emphasize.txt              # Emphasis notes
│   ├── examples.txt               # Examples
│   └── examples copy.txt
│
├── tests/                          # Tests
│   ├── conftest.py               # pytest configuration
│   └── test_karma.py             # Core tests
│
├── docs/                           # Documentation
│   └── refactoring_plan.md       # Refactoring plan document
│
├── data/                           # Runtime data (auto-created)
│   ├── memory/                    # Memory data
│   ├── logs/                     # Log output
│   ├── outputs/                  # Output (agent POV, top-down view)
│   └── videos/                   # Video files
│
├── environment.yml                 # Conda environment configuration
├── pyproject.toml                  # Python project configuration
└── README.md                       # This file
```

---

## Running

### CLI Mode

Execute a single task from the command line:

```bash
# Basic usage
python -m scripts.main --task "pick up the apple"

# Specify scene
python -m scripts.main --task "turn on the lamp" --scene FloorPlan3

# Verbose logging mode
python -m scripts.main --task "wash the tomato" --verbose

# Use a specific config file
python -m scripts.main --task "slice the bread" --config configs/experiment/complex.yaml
```

### GUI Mode

Launch the graphical interface:

```bash
python -m scripts.main --gui
```

---

## Configuration

### Configuration Loading Order

1. `configs/default.yaml` — base configuration
2. `configs/api.yaml` — API credentials override
3. Command-line `--config` argument — experiment config override
4. Command-line `--scene` / `--verbose` arguments — individual parameter overrides

### Configuration File Reference

| Setting | Description | Example |
|---------|-------------|---------|
| `api.api_key` | OpenAI API key | `${OPENAI_API_KEY}` env var |
| `api.base_url` | API base URL | `https://api.chatanywhere.tech/v1` |
| `api.model_name` | Model name | `gpt-4o` |
| `agent.scene` | AI2-THOR scene | `FloorPlan1` |
| `agent.grid_size` | Navigation grid size | `0.25` |
| `agent.goal_threshold` | Navigation arrival threshold | `0.3` |
| `memory.similarity_threshold` | Similarity threshold | `0.3` |
| `memory.exploration_positions` | Exploration position list | `[[1.25, 0, -1.75], ...]` |
| `logging.level` | Log level | `INFO` / `DEBUG` |

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `KARMA_BASE_PATH` | Project root directory | No (default: `/root/autodl-tmp/KARMA`) |

---

## Refactoring

This branch (`refactor`) performed a comprehensive refactoring of the original codebase to address a series of long-standing engineering issues.

### Pre-refactoring Problems

#### Problem 1: Files with Overly Concentrated Responsibilities

| Original File | Lines | Issue |
|--------------|-------|-------|
| `execute_LLM_plan.py` | 1089 | Controller init, navigation, action execution, and memory management all mixed together |
| `run_without_GUI_api.py` | 2265 | Large amounts of hardcoded test tasks mixed with execution logic |
| `ai2_thor_controller.py` | 524 | Highly overlapping functionality with `execute_LLM_plan.py` |

#### Problem 2: Code Duplication (~1500+ lines)

The following functions were completely duplicated across two files:

```
GoToObject              (466-557 vs 258-355)
ExploreObject           (559-674 vs 357-472)
GoToObject_next_time    (675-784 vs 473-596)
GoToObject_with_memory  (785-872 vs 597-702)
PickupObject / PutObject / SwitchOn / SwitchOff /
OpenObject / CloseObject / SliceObject / CleanObject / ThrowObject
  — all completely duplicated
```

#### Problem 3: Hardcoding

- API key written directly in code (security risk)
- Magic numbers scattered throughout (`goal_thresh = 0.3`, `dist_del < 0.2`, `count_since_update < 15`, etc.)
- Exploration positions hardcoded in multiple places
- BASE_PATH defined repeatedly

#### Problem 4: Lack of Observability

- Only simple `print()` statements
- No log level control
- No structured logging
- No experiment tracking

#### Problem 5: Global State Abuse

```python
# Global variables in original code
c = Controller(...)              # global controller
action_queue = []               # global action queue
task_over = False               # global termination flag
robots = [{'name': 'robot1'}]  # global robot definition
reachable_positions = [...]     # global reachable positions
```

### Post-refactoring Improvements

#### Improvement 1: Clear Module Boundaries

```
karma/
├── agents/       → Robot, navigation, controller, skills — single responsibility
├── memory/      → Short/long/semantic memory — modular
├── planning/    → Task decomposition, LLM planning, execution — clear pipeline
├── perception/  → Image analysis, state recognition, similarity — perception isolated
├── utils/       → Logging, paths, files — utilities centralized
└── gui/         → Tkinter interface — UI isolated
```

#### Improvement 2: Zero Code Duplication

All navigation functions (GoToObject, ExploreObject, Explore, etc.) defined in only one place:
- `karma/agents/navigation.py` — single authoritative source
- `karma/agents/skills.py` — all skills defined once

#### Improvement 3: Configuration Externalization

| Setting | Before | After |
|---------|--------|-------|
| API Key | Hardcoded in code | Environment variable `OPENAI_API_KEY` |
| Model config | Hardcoded in code | `configs/api.yaml` |
| Experiment parameters | Hardcoded in code | `configs/experiment/*.yaml` |
| Path config | Hardcoded in multiple places | `configs/default.yaml` + relative paths |
| Magic numbers | Scattered everywhere | Centralized in `karma/constants.py` |

#### Improvement 4: Full Observability

| Feature | Implementation |
|---------|----------------|
| Structured logging | `karma/utils/logger.py` — colored console output + file output |
| Experiment tracking | `ExperimentLogger` class — records params, result, duration for every action |
| Experiment summary | Auto-generates `*_summary.json` with success rate statistics |
| Log level control | `--verbose` flag switches between INFO/DEBUG |

#### Improvement 5: Backward Compatibility

Legacy files (`execute_LLM_plan.py`, `run_without_GUI_api.py`, etc.) are preserved in the `scripts/` directory and remain independently runnable. New and old systems can run in parallel for gradual migration.

