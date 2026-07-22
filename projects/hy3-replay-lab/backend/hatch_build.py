from __future__ import annotations

from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    """Ship public fixtures and evaluations with both wheels and source archives."""

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        del version
        root = Path(self.root)
        resource_root = root if (root / "fixtures").is_dir() else root.parent
        if self.target_name == "sdist":
            destinations = {
                resource_root / "fixtures": "fixtures",
                resource_root / "evals" / "cases.json": "evals/cases.json",
                resource_root / "evals" / "annotations.json": "evals/annotations.json",
            }
        else:
            destinations = {
                resource_root / "fixtures": "replaylab/data/fixtures",
                resource_root / "evals" / "cases.json": "replaylab/data/evals/cases.json",
                resource_root
                / "evals"
                / "annotations.json": "replaylab/data/evals/annotations.json",
            }
        build_data["force_include"].update(
            {str(source): destination for source, destination in destinations.items()}
        )
