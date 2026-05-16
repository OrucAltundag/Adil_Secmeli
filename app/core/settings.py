# -*- coding: utf-8 -*-
"""
Environment + config.json tabanli merkezi ayarlar.

Bu modül geriye uyumluluk için korunmuştur. Yeni kod doğrudan
app.core.config.load_app_config() kullanmalıdır.
"""

from __future__ import annotations

from dataclasses import dataclass
from app.core.config import load_app_config as _load_app_config


@dataclass
class AppSettings:
    db_path: str
    db_url: str
    api_host: str
    api_port: int
    log_level: str
    enable_yearly_criteria_workflow: bool


def load_settings(config_path: str = "config.json") -> AppSettings:
    """load_app_config() üzerinden AppSettings oluşturur (geriye uyumluluk)."""
    cfg = _load_app_config(config_path=config_path)
    return AppSettings(
        db_path=cfg.sqlite_db_path,
        db_url=cfg.database_url,
        api_host=cfg.api_host,
        api_port=cfg.api_port,
        log_level=cfg.log_level,
        enable_yearly_criteria_workflow=cfg.enable_yearly_criteria_workflow,
    )
