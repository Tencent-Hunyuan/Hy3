from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Mapping


API_DIR = Path(__file__).resolve().parents[1]
ROOT = API_DIR.parents[1]


def load_example(filename: str) -> ModuleType:
    path = API_DIR / filename
    module_name = f"hy3_example_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载示例模块：{filename}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise RuntimeError(f"执行示例模块失败：{filename}") from error
    return module


def run_example(
    filename: str,
    *arguments: str,
    extra_env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    if extra_env is not None:
        environment.update(extra_env)
    return subprocess.run(
        [sys.executable, API_DIR / filename, *arguments],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
