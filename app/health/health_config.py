# -*- coding: utf-8 -*-
"""Sağlık kontrolleri için ayarlanabilir eşikler ve beklenen yapılar."""

from __future__ import annotations

from pathlib import Path


ROOT_PATH = Path(__file__).resolve().parents[2]
EXPECTED_MIN_TABLE_COUNT = 20
DB_CONNECTION_WARNING_MS = 100.0
DB_CONNECTION_CRITICAL_MS = 1000.0
QUERY_WARNING_MS = 500.0
QUERY_CRITICAL_MS = 1000.0
AHP_WEIGHT_TOLERANCE = 0.001
AHP_CR_WARNING = 0.10
AHP_CR_CRITICAL = 0.20

EXPECTED_TABLES = {
    "ders": {"required_columns": ("ders_id", "ad")},
    "fakulte": {"required_columns": ("fakulte_id", "ad")},
    "bolum": {"required_columns": ("bolum_id", "ad")},
    "havuz": {"required_columns": ("ders_id",)},
    "ahp_weight_profiles": {"required_columns": ("weights_json", "consistency_ratio")},
    "decision_runs": {"required_columns": ("id", "status")},
}

CRITICAL_IMPORTS = (
    "app.core.config",
    "app.db.session",
    "app.services.system_service",
    "app.services.calculation",
    "app.services.ahp_calculation_service",
    "app.ui.tabs.system_health_page",
)

REPORT_DIR_NAME = "reports"
LOG_DIR_NAME = "logs"
BACKUP_DIR_NAME = "backups"
