# -*- coding: utf-8 -*-
"""
Environment + config.json tabanli merkezi ayarlar.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - opsiyonel bagimlilik
    load_dotenv = None


@dataclass
class AppSettings:
    db_path: str
    db_url: str
    api_host: str
    api_port: int
    log_level: str
    enable_yearly_criteria_workflow: bool


def _load_json_config(config_path: str = "config.json") -> dict:
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def load_settings(config_path: str = "config.json") -> AppSettings:
    if load_dotenv is not None:
        load_dotenv(override=False)

    cfg = _load_json_config(config_path=config_path)

    default_db_path = cfg.get("db_path", os.getenv("DB_PATH", "./data/adil_secmeli.db"))
    db_path = os.getenv("DB_PATH", default_db_path)
    db_path = str(Path(db_path))

    default_db_url = cfg.get("db_url", f"sqlite:///{Path(db_path).resolve()}")
    db_url = os.getenv("DATABASE_URL", default_db_url)

    api_host = os.getenv("API_HOST", cfg.get("api_host", "0.0.0.0"))
    api_port = int(os.getenv("API_PORT", cfg.get("api_port", 8000)))
    log_level = os.getenv("LOG_LEVEL", cfg.get("log_level", "INFO"))
    workflow_raw = os.getenv(
        "ENABLE_YEARLY_CRITERIA_WORKFLOW",
        str(cfg.get("enable_yearly_criteria_workflow", True)),
    )
    enable_yearly_criteria_workflow = str(workflow_raw).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    return AppSettings(
        db_path=db_path,
        db_url=db_url,
        api_host=api_host,
        api_port=api_port,
        log_level=log_level,
        enable_yearly_criteria_workflow=enable_yearly_criteria_workflow,
    )
