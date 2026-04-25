# -*- coding: utf-8 -*-
"""Ortak logging yapılandırması."""

from __future__ import annotations

import logging
import sys

from app.core.config import AppConfig, load_app_config


def configure_logging(config: AppConfig | None = None) -> None:
    cfg = config or load_app_config()
    level = getattr(logging, str(cfg.log_level).upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=False,
    )
    logging.getLogger("app").setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
