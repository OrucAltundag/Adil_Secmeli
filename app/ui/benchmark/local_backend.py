# -*- coding: utf-8 -*-
"""In-process (yerel) benchmark backend.

HTTP API (FastAPI 127.0.0.1:8000) çalışmadığında, statik mock yerine GERÇEK
servisleri aynı süreç içinde çağırarak canlı veri üretir. Böylece "Çalıştır"
butonu API olmadan da gerçek hesaplama yapar (statik/mock veri kuralı).

Tasarım:
- Her fonksiyon kendi SQLite bağlantısını açar/kapatır (API route'larıyla aynı
  bağlantı çözümü: load_app_config().sqlite_db_path + ensure_reporting_schema).
- Dönüş şekilleri api_client'ın beklediği HTTP yanıtlarıyla birebir eşleşir:
  scenarios/algorithms -> {"scenarios":[...]} / {"algorithms":[...]}
  diğerleri -> _api_response zarfı: {"data":..., "message":..., "warnings":[], "meta":{}}
- Bir eşleme gerçek veriyle çözülemezse exception fırlatır; api_client mock'a düşer.
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict
from typing import Any

from app.core.config import load_app_config
from app.db.backend import is_sqlite_url
from app.db.sqlite_connection import connect_sqlite


def _envelope(data: Any, message: str | None = None) -> dict[str, Any]:
    return {"data": data, "message": message, "warnings": [], "meta": {}}


def _open_connection() -> sqlite3.Connection:
    """Yerel okuma/çalıştırma bağlantısı.

    Şema mutasyonu (ensure_reporting_schema) BURADA yapılmaz: registry ve
    governed-run tabloları uygulama açılışında zaten oluşturulmuştur; her
    çağrıda mutasyon hem gereksiz hem de 'database is locked' riski yaratır.
    Eşzamanlı erişimde beklemek için busy_timeout ayarlanır.
    """
    cfg = load_app_config()
    if not is_sqlite_url(cfg.database_url):
        raise RuntimeError("Yerel backend yalnızca SQLite yapılandırmasında çalışır.")
    conn = connect_sqlite(cfg.sqlite_db_path, row_factory=True)
    try:
        conn.execute("PRAGMA busy_timeout = 8000")
    except sqlite3.Error:
        pass
    return conn


# --- Senaryo / algoritma kataloğu (registry tabanlı, gerçek) ---------------

def get_scenarios() -> dict[str, Any]:
    from app.benchmark.scenarios import DEFAULT_SCENARIOS, display_label

    scenarios = []
    for scenario in DEFAULT_SCENARIOS.values():
        item = asdict(scenario)
        item["label"] = display_label(scenario)
        scenarios.append(item)
    return {"scenarios": scenarios}


def get_algorithms() -> dict[str, Any]:
    from app.services.algorithm_governance_service import list_algorithm_governance

    conn = _open_connection()
    try:
        rows = list_algorithm_governance(conn)
    finally:
        conn.close()
    return {"algorithms": rows}


# --- Algoritma yönetişimi (governance) -------------------------------------

def get_algorithm_governance() -> dict[str, Any]:
    from app.services.algorithm_governance_service import list_algorithm_governance

    conn = _open_connection()
    try:
        data = list_algorithm_governance(conn)
    finally:
        conn.close()
    return _envelope(data, "Algoritma yönetişimi registry listelendi (yerel).")


def set_algorithm_active(algorithm_key: str, is_active: bool) -> dict[str, Any]:
    from app.services.algorithm_governance_service import (
        set_algorithm_active as _set_active,
    )

    conn = _open_connection()
    try:
        result = _set_active(conn, algorithm_key, bool(is_active))
        conn.commit()
    finally:
        conn.close()
    durum = "aktif" if is_active else "pasif"
    return _envelope(result, f"Algoritma {durum} hale getirildi (yerel).")


def get_algorithm_tasks() -> dict[str, Any]:
    from app.services.algorithm_governance_service import list_task_mappings

    conn = _open_connection()
    try:
        data = list_task_mappings(conn)
    finally:
        conn.close()
    return _envelope(data, "Problem-algoritma eşleştirme matrisi listelendi (yerel).")


# --- Governed benchmark çalıştırmaları (gerçek hesaplama) ------------------

def get_governed_runs(limit: int = 100) -> dict[str, Any]:
    from app.services.governed_benchmark_service import list_governed_benchmark_runs

    conn = _open_connection()
    try:
        data = list_governed_benchmark_runs(conn, limit=limit)
        conn.commit()
    finally:
        conn.close()
    return _envelope(data, "Governed benchmark çalıştırmaları listelendi (yerel).")


def execute_governed_run(payload: dict[str, Any]) -> dict[str, Any]:
    from app.services.governed_benchmark_service import execute_governed_benchmark_run

    conn = _open_connection()
    try:
        result = execute_governed_benchmark_run(conn, payload)
        conn.commit()
    finally:
        conn.close()
    return _envelope(result, "Governed benchmark çalıştırması tamamlandı (yerel).")


def _governed_run_subresource(run_id: int | str, getter_name: str, label: str) -> dict[str, Any]:
    import app.services.governed_benchmark_service as svc

    getter = getattr(svc, getter_name)
    conn = _open_connection()
    try:
        data = getter(conn, int(run_id))
        conn.commit()
    finally:
        conn.close()
    return _envelope(data, f"{label} (yerel).")


def get_governed_run_metrics(run_id: int | str) -> dict[str, Any]:
    return _governed_run_subresource(run_id, "get_governed_run_metrics", "Çalıştırma metrikleri")


def get_governed_run_validation(run_id: int | str) -> dict[str, Any]:
    return _governed_run_subresource(run_id, "get_governed_run_validation", "Çalıştırma doğrulaması")


def get_governed_run_statistics(run_id: int | str) -> dict[str, Any]:
    return _governed_run_subresource(run_id, "get_governed_run_statistics", "İstatistiksel karşılaştırma")


def get_governed_run_diagnostics(run_id: int | str) -> dict[str, Any]:
    return _governed_run_subresource(run_id, "get_governed_run_diagnostics", "Model tanılaması")


def get_governed_run_leakage(run_id: int | str) -> dict[str, Any]:
    return _governed_run_subresource(run_id, "get_governed_run_leakage", "Veri sızıntısı kontrolü")


def get_governed_run_clustering(run_id: int | str) -> dict[str, Any]:
    return _governed_run_subresource(run_id, "get_governed_run_clustering", "Kümeleme değerlendirmesi")
