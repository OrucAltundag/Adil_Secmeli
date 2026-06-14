# -*- coding: utf-8 -*-
"""Sağlık kontrolleri için ayarlanabilir yapılandırma.

Beklenen tablo/kolonlar, eşik değerleri ve klasör yolları burada
toplanır. Proje yapısı değişirse sadece bu dosya güncellenir; kontroller
sabit değer içermez.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# app/health/health_config.py -> proje kökü iki üst klasör.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class QueryThresholds:
    """Sorgu/bağlantı süre eşikleri (ms)."""

    ok_ms: float = 100.0
    warning_ms: float = 500.0
    critical_ms: float = 1000.0
    connection_ok_ms: float = 150.0
    connection_warning_ms: float = 600.0


@dataclass(frozen=True)
class HealthConfig:
    """Sağlık merkezi yapılandırması."""

    project_root: Path = PROJECT_ROOT

    # --- Beklenen şema (schema_health_service ile uyumlu çekirdek) ---
    expected_tables: tuple[str, ...] = (
        "ders",
        "fakulte",
        "bolum",
        "ders_kriterleri",
        "havuz",
        "skor",
        "schema_compat_logs",
        "sql_console_audit_logs",
    )
    expected_columns: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            "ders": ("ders_id", "ad"),
            "ders_kriterleri": ("ders_id", "yil", "donem"),
            "havuz": ("ders_id", "yil", "statu"),
        }
    )
    min_table_count: int = 20

    # --- Veri kalitesi ---
    critical_not_null: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            "ders": ("ders_id", "ad"),
            "havuz": ("ders_id", "yil"),
            "ders_kriterleri": ("ders_id", "yil"),
        }
    )
    duplicate_keys: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            # Aynı ders aynı yıl iki farklı dönemde (Güz/Bahar) açılabilir;
            # benzersizlik anahtarı 'donem' içermeli. 'donem' olmadan Güz/Bahar
            # kayıtları yanlışlıkla tekrar olarak işaretleniyordu (false positive).
            "havuz": ("ders_id", "yil", "donem"),
            "ders_kriterleri": ("ders_id", "yil", "donem"),
        }
    )
    non_negative_columns: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            "ders": ("kredi", "kontenjan", "akts"),
            "ders_kriterleri": (
                "toplam_ogrenci",
                "gecen_ogrenci",
                "kontenjan",
                "kayitli_ogrenci",
            ),
            "havuz": ("sayac",),
        }
    )
    profiling_tables: tuple[str, ...] = (
        "ders",
        "havuz",
        "ders_kriterleri",
        "fakulte",
        "bolum",
    )
    outlier_targets: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            "ders": ("kredi", "akts"),
            "ders_kriterleri": ("toplam_ogrenci", "basari_ortalamasi"),
        }
    )

    # --- AHP ---
    ahp_weight_sum_tolerance: float = 0.001
    ahp_cr_ok: float = 0.10
    ahp_cr_warning: float = 0.20

    # --- Eşikler ---
    thresholds: QueryThresholds = field(default_factory=QueryThresholds)
    large_table_row_limit: int = 1000
    table_preview_limit: int = 10
    backup_max_age_days: int = 7
    slow_query_ms: float = 500.0

    # --- Import edilebilir kritik modüller ---
    critical_modules: tuple[str, ...] = (
        "app.core.config",
        "app.core.result",
        "app.db.session",
        "app.services.system_service",
        "app.services.service_factory",
        "app.services.schema_health_service",
        "app.services.architecture_audit_service",
        "app.algorithms.mcdm.ahp",
        "app.algorithms.mcdm.topsis",
    )

    # --- Klasör yolları (proje köküne göre) ---
    data_dir: str = "data"
    logs_dir: str = "logs"
    reports_dir: str = "reports"
    backups_dir: str = "data/backups"
    config_files: tuple[str, ...] = ("config.json", "alembic.ini", "requirements.txt")

    # --- Kritik sorgular (performans/karar için) ---
    performance_queries: dict[str, str] = field(
        default_factory=lambda: {
            "ders_count": "SELECT COUNT(*) FROM ders",
            "havuz_join": (
                "SELECT h.ders_id, h.yil, h.statu FROM havuz h "
                "LEFT JOIN ders d ON d.ders_id = h.ders_id LIMIT 200"
            ),
            "kriter_scan": "SELECT ders_id, yil, donem FROM ders_kriterleri LIMIT 200",
        }
    )

    def path(self, *parts: str) -> Path:
        return self.project_root.joinpath(*parts)

    def data_path(self) -> Path:
        return self.path(self.data_dir)

    def logs_path(self) -> Path:
        return self.path(self.logs_dir)

    def reports_path(self) -> Path:
        return self.path(self.reports_dir)

    def backups_path(self) -> Path:
        return self.path(self.backups_dir)


_DEFAULT = HealthConfig()


def default_health_config() -> HealthConfig:
    """Varsayılan (paylaşılan) sağlık yapılandırmasını döndürür."""

    return _DEFAULT
