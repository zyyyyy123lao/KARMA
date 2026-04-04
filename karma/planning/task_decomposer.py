"""LLM-powered task decomposer for KARMA.

Breaks down high-level task descriptions into executable Python code
using the GPT model, based on available skills and experience.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from karma.config import APIConfig
from karma.utils.file_utils import write_text

logger = logging.getLogger("karma.planning.decomposer")


class TaskDecomposer:
    """Decomposes natural language tasks into Python code using LLM.

    Loads skill definitions, role prompts, and experience examples,
    then uses the LLM to generate executable task functions.
    """

    def __init__(self, api_config: Optional[APIConfig] = None):
        self.api_config = api_config or APIConfig()
        self._openai_configured = False

    def _ensure_openai_configured(self) -> None:
        if self._openai_configured:
            return
        import openai as _openai_module
        _openai_module.api_key = self.api_config.api_key
        _openai_module.api_base = self.api_config.base_url
        self._openai_configured = True

    def build_messages(
        self,
        task_description: str,
        paths,
        use_short_term_memory: bool = False,
    ) -> List[Dict[str, str]]:
        """Build the messages list for the LLM prompt.

        Args:
            task_description: The task to decompose.
            paths: PathResolver instance for finding prompt files.
            use_short_term_memory: Whether to include short-term memory in prompt.
        """
        from karma.utils.file_utils import read_text

        messages = []

        # Skill definitions
        skills = read_text(paths.skills)
        messages.append({"role": "user", "content": skills})

        # Action examples
        actions = read_text(paths.resources / "actions.py")
        messages.append({"role": "user", "content": actions})

        # System role
        role = read_text(paths.role)
        messages.append({"role": "system", "content": role})

        # Task examples
        examples = read_text(paths.examples)
        messages.append({"role": "user", "content": examples})

        # Emphasis
        emphasize = read_text(paths.emphasize)
        messages.append({"role": "user", "content": emphasize})

        # Long-term memory (scene layout)
        long_term = read_text(paths.long_term_memory_prompt)
        messages.append({"role": "user", "content": long_term})

        # CRITICAL: available action wrapper functions (authoritative list)
        # The generated code MUST only call functions defined in scripts/action_wrappers.py.
        # Never invent function names not listed here.
        import inspect
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "action_wrappers",
            paths.base / "scripts" / "action_wrappers.py",
        )
        wrapper_src = ""
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            wrapper_funcs = [
                name for name, obj in vars(mod).items()
                if callable(obj) and not name.startswith("_")
            ]
            wrapper_src = (
                "AVAILABLE FUNCTIONS (use ONLY these names from action_wrappers.py):\n"
                + "\n".join(f"  - {fn}" for fn in sorted(wrapper_funcs))
                + "\n"
            )
        messages.append({"role": "system", "content": wrapper_src})

        # Task instruction
        instruction = (
            f"Please help me decompose the following task: {task_description}.\n"
            f"You MUST only call functions listed in the AVAILABLE FUNCTIONS above.\n"
            f"Do NOT invent or rename functions (e.g. use 'CleanObject', NOT 'Clean' or 'Wash').\n"
            f"Please output only the generated Python code."
        )
        messages.append({"role": "user", "content": instruction})

        return messages

    def decompose(
        self,
        task_description: str,
        paths,
        use_short_term_memory: bool = False,
    ) -> str:
        """Generate Python code for a task description.

        Args:
            task_description: The natural language task.
            paths: PathResolver for prompt files.
            use_short_term_memory: Include short-term memory in prompt.

        Returns:
            The generated Python code as a string.
        """
        messages = self.build_messages(
            task_description, paths, use_short_term_memory
        )

        # Save messages for debugging
        write_text(paths.messages, json.dumps(messages, indent=2, ensure_ascii=False))

        self._ensure_openai_configured()
        import openai as _openai_module
        try:
            response = _openai_module.ChatCompletion.create(
                model=self.api_config.model_name,
                messages=messages,
                max_tokens=self.api_config.max_tokens,
                temperature=self.api_config.temperature,
            )
            content = response.choices[0].message.content.strip()
            logger.info("Task decomposition successful: %s", task_description)
            return content
        except Exception as e:
            logger.error("Task decomposition failed: %s", e)
            return ""

    def parse_code(self, raw_response: str) -> str:
        """Extract Python code from the LLM response.

        Strips markdown code fences and metadata.
        """
        lines = raw_response.split("\n")
        code_lines = []
        in_code = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code = not in_code
                continue
            if in_code or (not lines[0].strip().startswith("```") and code_lines):
                code_lines.append(line)

        return "\n".join(code_lines).strip()

    def save_generated_code(
        self,
        code: str,
        output_path: str | Path,
        name_path: Optional[str | Path] = None,
    ) -> Optional[str]:
        """Save generated code to a Python file.

        Args:
            code: The generated Python code.
            output_path: Path to the task_functions.py file.
            name_path: Optional path to save the function name JSON.
                       Defaults to output_path's parent / "generated_function_name.json".

        Returns:
            The extracted function name.
        """
        parsed = self.parse_code(code)

        # Extract function name
        func_name = None
        for line in parsed.split("\n"):
            if line.strip().startswith("def "):
                func_name = line.split("(")[0].split()[1]
                break

        # Write the full file: header + import + all functions (replace existing)
        path = Path(output_path)
        content = (
            '"""Auto-generated task functions.\n\n'
            'This file is auto-generated by KARMA\'s task decomposition system.\n'
            'Do not edit this file manually.\n'
            '"""\n'
            'from scripts.action_wrappers import *\n\n'
            f'{parsed}\n'
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        # Save function name
        if func_name:
            save_path = Path(name_path) if name_path else path.parent / "generated_function_name.json"
            write_text(save_path, json.dumps({"function_name": func_name}))

        logger.info("Saved generated code, function: %s", func_name)
        return func_name