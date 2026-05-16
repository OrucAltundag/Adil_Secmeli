# -*- coding: utf-8 -*-
"""Bağımlılık tarayıcı.

requirements.txt ile gerçek import kullanımı arasındaki farkları
raporlar. Paket KURMAZ; yalnızca tespit eder.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Python 3.10+ standart kütüphane modül adları (false-positive engeller).
_STDLIB = set(getattr(sys, "stdlib_module_names", set()))

from app.health.health_config import HealthConfig, default_health_config

# import adı -> requirements'taki dağıtım adı eşlemesi.
IMPORT_TO_DIST = {
    "sklearn": "scikit-learn",
    "dotenv": "python-dotenv",
    "cv2": "opencv-python",
    "PIL": "pillow",
    "yaml": "pyyaml",
    "psycopg2": "psycopg2-binary",
}

# Bilinen birinci-parti / stdlib kökleri (tarama dışı bırakılır).
_STDLIB_HINT = {
    "os", "sys", "re", "json", "time", "math", "io", "csv", "abc", "enum",
    "typing", "pathlib", "dataclasses", "datetime", "logging", "sqlite3",
    "threading", "queue", "contextlib", "importlib", "argparse", "collections",
    "functools", "itertools", "statistics", "traceback", "tempfile", "shutil",
    "subprocess", "unittest", "warnings", "platform", "uuid", "hashlib",
    "secrets", "string", "random", "glob", "copy", "inspect", "operator",
    "app", "tests", "alembic", "tkinter", "concurrent", "asyncio", "base64",
}

_CRITICAL = {"pandas", "numpy", "sqlalchemy", "fastapi"}

# fastapi/uvicorn ile gelen ya da yalnızca geliştirme/test amaçlı paketler;
# requirements'ta ayrıca aranmaz (gürültüyü azaltır).
_TRANSITIVE_OR_DEV = {"starlette", "pydantic", "pytest", "anyio", "click", "h11"}

_IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z_][\w]*)")


@dataclass
class DependencyScanResult:
    requirements_present: bool = False
    pyproject_present: bool = False
    declared: list[str] = field(default_factory=list)
    used_not_declared: list[str] = field(default_factory=list)
    declared_not_used: list[str] = field(default_factory=list)
    missing_critical: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirements_present": self.requirements_present,
            "pyproject_present": self.pyproject_present,
            "declared": sorted(self.declared),
            "used_not_declared": sorted(self.used_not_declared),
            "declared_not_used": sorted(self.declared_not_used),
            "missing_critical": sorted(self.missing_critical),
        }


def _parse_requirements(path: Path) -> list[str]:
    names: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name = re.split(r"[<>=!\[ ]", line, 1)[0].strip().lower()
        if name:
            names.append(name)
    return names


def _collect_imports(app_dir: Path) -> set[str]:
    found: set[str] = set()
    for py in app_dir.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        try:
            for line in py.read_text(encoding="utf-8", errors="ignore").splitlines():
                m = _IMPORT_RE.match(line)
                if m:
                    found.add(m.group(1))
        except OSError:
            continue
    return found


def scan_dependencies(config: HealthConfig | None = None) -> DependencyScanResult:
    cfg = config or default_health_config()
    root = cfg.project_root
    result = DependencyScanResult()

    req_path = root / "requirements.txt"
    result.requirements_present = req_path.exists()
    result.pyproject_present = (root / "pyproject.toml").exists()
    declared = set(_parse_requirements(req_path)) if req_path.exists() else set()
    result.declared = sorted(declared)

    imports = _collect_imports(root / "app")
    third_party = {
        imp
        for imp in imports
        if imp not in _STDLIB_HINT
        and imp not in _STDLIB
        and not imp.startswith("_")
    }

    used_dist = {IMPORT_TO_DIST.get(imp, imp).lower() for imp in third_party}
    result.used_not_declared = sorted(
        d
        for d in used_dist
        if d not in declared
        and d not in _STDLIB_HINT
        and d not in _TRANSITIVE_OR_DEV
    )
    # declared_not_used: kabaca; import adıyla birebir eşleşmeyen dağıtımlar.
    used_norm = used_dist | {imp.lower() for imp in third_party}
    result.declared_not_used = sorted(
        d for d in declared if d not in used_norm and d.replace("-", "_") not in used_norm
    )
    result.missing_critical = sorted(
        c for c in _CRITICAL if c not in declared
    )
    return result
