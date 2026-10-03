"""
Prompt Registry — Centralized Versioned Prompt Management
=========================================================
Every prompt must be loaded through this registry.
Prompts are stored as YAML files in /prompts/<task>/<version>.yaml
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_PROMPTS_DIR = Path(__file__).parent.parent.parent.parent.parent / "prompts"


class PromptRegistry:
    """Loads and caches versioned prompts from YAML files."""

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}

    def get(self, task: str, version: str = "v1") -> dict[str, Any]:
        """Return the prompt definition for a given task and version."""
        key = f"{task}/{version}"
        if key not in self._cache:
            path = _PROMPTS_DIR / task / f"{version}.yaml"
            if not path.exists():
                raise FileNotFoundError(f"Prompt not found: {path}")
            with open(path, encoding="utf-8") as f:
                self._cache[key] = yaml.safe_load(f)
        return self._cache[key]

    def build_messages(
        self,
        task: str,
        variables: dict[str, str],
        version: str = "v1",
    ) -> list[dict[str, str]]:
        """Build a list of chat messages from the prompt template."""
        prompt = self.get(task, version)
        system_content = prompt["system"].strip()
        user_template = prompt.get("user_template", "{question}").strip()
        try:
            user_content = user_template.format(**variables)
        except KeyError as e:
            raise ValueError(f"Missing prompt variable: {e}") from e
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]


_registry: PromptRegistry | None = None


def get_prompt_registry() -> PromptRegistry:
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
    return _registry
