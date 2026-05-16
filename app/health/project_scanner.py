# -*- coding: utf-8 -*-
"""Proje yapısı tarayıcı.

Eksik klasörler, eksik config dosyaları, eksik ``__init__.py`` ve UI'da
doğrudan DB erişimi gibi yapısal sorunları (salt-okunur) tespit eder.
Hiçbir değişiklik yapmaz; yalnızca rapor üretir.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.health.health_config import HealthConfig, default_health_config


@dataclass
class ProjectScanResult:
    missing_dirs: list[str] = field(default_factory=list)
    missing_config_files: list[str] = field(default_factory=list)
    missing_init_files: list[str] = field(default_factory=list)
    ui_direct_db: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "missing_dirs": self.missing_dirs,
            "missing_config_files": self.missing_config_files,
            "missing_init_files": self.missing_init_files,
            "ui_direct_db": self.ui_direct_db,
            "ok": not (
                self.missing_dirs
                or self.missing_config_files
                or self.missing_init_files
            ),
        }


# Otomatik düzeltmeye uygun (oluşturulabilir) klasörler.
EXPECTED_DIRS = (
    "logs",
    "reports",
    "data/backups",
    "exports",
    "health_reports",
)


def scan_project(config: HealthConfig | None = None) -> ProjectScanResult:
    cfg = config or default_health_config()
    root = cfg.project_root
    result = ProjectScanResult()

    for rel in EXPECTED_DIRS:
        if not (root / rel).exists():
            result.missing_dirs.append(rel)

    for name in cfg.config_files:
        if not (root / name).exists():
            result.missing_config_files.append(name)

    health_root = root / "app" / "health"
    if health_root.exists():
        for pkg in [health_root, health_root / "checks"]:
            if pkg.is_dir() and not (pkg / "__init__.py").exists():
                result.missing_init_files.append(
                    str((pkg / "__init__.py").relative_to(root).as_posix())
                )

    try:
        from app.services.architecture_audit_service import (
            scan_ui_direct_db_access,
        )

        for finding in scan_ui_direct_db_access():
            if not finding.get("allowlisted"):
                result.ui_direct_db.append(
                    {
                        "file": finding.get("file"),
                        "line": finding.get("line"),
                        "pattern": finding.get("pattern"),
                    }
                )
    except Exception:  # noqa: BLE001 - tarayıcı asla çökmemeli
        pass

    return result


def missing_dirs_for_repair(config: HealthConfig | None = None) -> list[Path]:
    """Auto-repair'in güvenle oluşturabileceği eksik klasör yolları."""

    cfg = config or default_health_config()
    return [
        cfg.project_root / rel
        for rel in EXPECTED_DIRS
        if not (cfg.project_root / rel).exists()
    ]
