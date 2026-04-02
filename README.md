# KARMA - Embodied AI Agent with Memory Systems

> Augmenting Embodied AI Agents with Long-and-short Term Memory Systems

## Overview

KARMA is a research-grade embodied AI agent that uses GPT-4o for task planning combined with a three-tier memory architecture (short-term, long-term, semantic) to solve complex household tasks in the AI2-THOR simulation environment.

## Architecture

```
karma/
├── agents/       # Robot, navigation, controller, skills
├── memory/       # Short-term, long-term, semantic memory
├── perception/  # Image analysis, state recognition, similarity
├── planning/     # Task decomposition, LLM planner, executor
├── utils/       # Logging, paths, file utilities
├── gui/        # Tkinter-based graphical interface
└── config.py   # Singleton configuration manager
```

## Installation

```bash
conda env create -f environment.yml
conda activate karma
```

Or with pip:

```bash
pip install ai2thor numpy scipy opencv-python sentence-transformers pyyaml requests openai
```

## Quick Start

### CLI Mode

```bash
python -m scripts.main --task "wash the apple"
python -m scripts.main --task "slice the tomato" --scene FloorPlan2
python -m scripts.main --config configs/experiment/complex.yaml --verbose
```

### GUI Mode

```bash
python -m scripts.main --gui
```

### Run Experiments

```bash
python -m scripts.run_experiment --experiments configs/experiment
```

## Configuration

All settings are managed via YAML files in `configs/`:

- `configs/default.yaml` - Default configuration
- `configs/api.yaml` - API credentials (use environment variables)
- `configs/experiment/` - Pre-defined experiment configurations

Environment variables for sensitive data:

```bash
export OPENAI_API_KEY="your-key-here"
export KARMA_BASE_PATH="/path/to/karma"
```

## Key Features

- **Three-tier memory**: Short-term (dynamic), long-term (scene layout), semantic (experience)
- **LLM task decomposition**: GPT-4o generates executable Python from natural language
- **Vision-based state recognition**: GPT-4o analyzes frames to infer object states
- **Skill registry**: Extensible set of robot capabilities
- **Experiment tracking**: Structured logging and metric collection
- **GUI interface**: Tkinter app for task management and memory inspection

## Testing

```bash
pytest tests/ -v
```

## Documentation

- [Refactoring Plan](./docs/refactoring_plan.md) - Architecture and migration guide
- [docs/](./docs/) - Additional documentation

## License

MIT
