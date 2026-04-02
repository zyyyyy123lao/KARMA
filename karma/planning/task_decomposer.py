"""LLM-powered task decomposer for KARMA.

Breaks down high-level task descriptions into executable Python code
using the GPT model, based on available skills and experience.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from karma.config import APIConfig

logger = logging.getLogger("karma.planning.decomposer")


class TaskDecomposer:
    """Decomposes natural language tasks into Python code using LLM.

    Loads skill definitions, role prompts, and experience examples,
    then uses the LLM to generate executable task functions.
    """

    def __init__(self, api_config: Optional[APIConfig] = None):
        self.api_config = api_config or APIConfig()
        self._client = None

    @property
    def _openai_client(self):
        if self._client is None:
            import openai as _openai_module
            _openai_module.api_key = self.api_config.api_key
            _openai_module.api_base = self.api_config.base_url
            self._client = _openai_module.OpenAI(
                api_key=self.api_config.api_key,
                base_url=self.api_config.base_url,
            )
        return self._client

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

        # Task instruction
        instruction = f"Please help me decompose the following tasks: {task_description}. Please output only the generated code."
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
        from karma.utils.file_utils import write_text
        write_text(paths.messages, json.dumps(messages, indent=2, ensure_ascii=False))

        client = self._openai_client
        try:
            response = client.chat.completions.create(
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
        insert_line: int = 6,
    ) -> Optional[str]:
        """Save generated code to a Python file.

        Args:
            code: The generated Python code.
            output_path: Path to the task_functions.py file.
            insert_line: Line number at which to insert the code.

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

        # Insert into file
        from karma.utils.file_utils import insert_into_file, write_text
        insert_into_file(output_path, parsed, insert_line)

        # Save function name
        if func_name:
            name_path = Path(str(output_path).replace("task_functions.py", "generated_function_name.json"))
            write_text(name_path, json.dumps({"function_name": func_name}))

        logger.info("Saved generated code, function: %s", func_name)
        return func_name