from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
STATE_FILE = SKILL_DIR / ".runtime-bootstrap.json"

DEPENDENCIES = [
    {"import_name": "win32api", "package_name": "pywin32"},
    {"import_name": "win32con", "package_name": "pywin32"},
    {"import_name": "win32gui", "package_name": "pywin32"},
    {"import_name": "comtypes", "package_name": "comtypes>=1.2.0"},
    {"import_name": "pyperclip", "package_name": "pyperclip"},
    {"import_name": "markdown", "package_name": "markdown"},
    {"import_name": "bs4", "package_name": "beautifulsoup4"},
    {"import_name": "PIL", "package_name": "Pillow"},
    {"import_name": "yaml", "package_name": "pyyaml"},
]


def _read_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_state(payload: dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def inspect_runtime() -> dict[str, Any]:
    checks = []
    missing_imports = []
    package_names = []

    for item in DEPENDENCIES:
        import_name = item["import_name"]
        package_name = item["package_name"]
        try:
            module = importlib.import_module(import_name)
            checks.append(
                {
                    "import_name": import_name,
                    "package_name": package_name,
                    "ok": True,
                    "path": getattr(module, "__file__", "built-in"),
                }
            )
        except Exception as exc:
            checks.append(
                {
                    "import_name": import_name,
                    "package_name": package_name,
                    "ok": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            missing_imports.append(import_name)
            if package_name not in package_names:
                package_names.append(package_name)

    return {
        "checks": checks,
        "missing_imports": missing_imports,
        "missing_packages": package_names,
    }


def ensure_runtime(auto_install: bool = True) -> dict[str, Any]:
    before = inspect_runtime()
    installed = []
    state = _read_state()

    if before["missing_packages"] and auto_install:
        command = [sys.executable, "-m", "pip", "install", *before["missing_packages"]]
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        installed = list(before["missing_packages"])
        state = {
            "last_install_command": command,
            "last_install_returncode": completed.returncode,
            "installed_packages": installed,
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": completed.stderr[-4000:],
        }
        _write_state(state)
        if completed.returncode != 0:
            return {
                "ok": False,
                "auto_installed": installed,
                "checks": before["checks"],
                "missing_imports": before["missing_imports"],
                "missing_packages": before["missing_packages"],
                "pip_returncode": completed.returncode,
                "pip_stdout": completed.stdout[-4000:],
                "pip_stderr": completed.stderr[-4000:],
            }

    after = inspect_runtime()
    return {
        "ok": not after["missing_packages"],
        "auto_installed": installed,
        "checks": after["checks"],
        "missing_imports": after["missing_imports"],
        "missing_packages": after["missing_packages"],
        "state_file": str(STATE_FILE),
        "bootstrap_state": state if state else _read_state(),
    }
