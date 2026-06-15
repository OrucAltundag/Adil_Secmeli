# -*- coding: utf-8 -*-
"""Algoritma aktivite servisi (Faz D, spec madde 24-25).

Salt-okunur. `decision_runs` tablosundan son N karar calistirmasini zenginlestirip
"Algoritma Kullanim/Izleme Merkezi" niteliginde ozet doner.

Spec madde 25 ihtiyaclari:
- AHP ne zaman calisti, hangi profil?
- TOPSIS ne zaman calisti?
- Trend hesaplama
- LR/RF/DT calisti mi? (advisory_ml)
- Kac ders islendi?
- Sure?
- Hata/uyari var mi?

Bu servis decision_run kayitlarini okur (orada AHP profil snapshot ve zaman var);
ML aktivitesi varsa `algorithm_governance` katmaniyla zenginlestirir.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any


def _safe_json(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


def _duration_seconds(started: str | None, completed: str | None) -> float | None:
    """ISO zaman damgalari arasi sure (saniye). Hata olursa None."""
    if not started or not completed:
        return None
    from datetime import datetime

    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            s = datetime.strptime(started, fmt)
            c = datetime.strptime(completed, fmt)
            return (c - s).total_seconds()
        except ValueError:
            continue
    return None


def get_recent_activity(
    conn: sqlite3.Connection,
    limit: int = 20,
    year: int | None = None,
    faculty_id: int | None = None,
) -> list[dict[str, Any]]:
    """Son karar calistirmalarini zenginlestirilmis ozetle doner.

    Her satir tek bir decision_run'a denk gelir; AHP profil bilgisi, sure,
    durum, kapsam (fakulte+yil+donem) ve ders sayisi (mumkunse) icerir.
    """
    cur = conn.cursor()
    where = ["1=1"]
    params: list[Any] = []
    if year is not None:
        where.append("dr.year = ?")
        params.append(int(year))
    if faculty_id is not None:
        where.append("dr.faculty_id = ?")
        params.append(int(faculty_id))

    cur.execute(
        f"""
        SELECT dr.id, dr.year, dr.faculty_id, dr.semester, dr.status,
               dr.started_at, dr.completed_at, dr.ahp_profile_id,
               dr.ahp_profile_version, dr.ahp_weights_snapshot_json,
               dr.ahp_consistency_ratio, dr.ahp_profile_source,
               dr.summary_json, dr.error_message, dr.stale_flag,
               COALESCE(f.ad, '?') AS fakulte_adi
        FROM decision_runs dr
        LEFT JOIN fakulte f ON f.fakulte_id = dr.faculty_id
        WHERE {' AND '.join(where)}
        ORDER BY dr.id DESC
        LIMIT ?
        """,
        tuple(params + [int(limit)]),
    )

    # Onemli: cur.fetchall'i ONCE bitir, SONRA sqlite_master kontrolu yap.
    # Aksi halde yeni cur.execute, onceki SELECT'in sonuclarini siler ve liste bos doner.
    rows = cur.fetchall()

    # Ders sayisi: course_decisions tablosu varsa run basina sayar
    aux_cur = conn.cursor()
    has_course_decisions = bool(
        aux_cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='course_decisions' LIMIT 1"
        ).fetchone()
    )

    out: list[dict[str, Any]] = []
    for row in rows:
        run_id = int(row[0])
        weights = _safe_json(row[9]) or {}
        summary = _safe_json(row[12]) or {}
        ders_sayisi: int | None = None
        if has_course_decisions:
            try:
                aux_cur.execute(
                    "SELECT COUNT(*) FROM course_decisions WHERE decision_run_id = ?",
                    (run_id,),
                )
                ders_sayisi = int((aux_cur.fetchone() or [0])[0] or 0)
            except sqlite3.OperationalError:
                ders_sayisi = None
        # summary_json icindeki bilinen alanlar (record_decision_run_for_faculty_year yazar)
        for key in ("course_count", "total_courses", "scored_count"):
            if ders_sayisi in (None, 0) and key in summary:
                try:
                    ders_sayisi = int(summary[key])
                except (TypeError, ValueError):
                    pass

        out.append(
            {
                "run_id": run_id,
                "yil": int(row[1]) if row[1] is not None else None,
                "fakulte_id": int(row[2]) if row[2] is not None else None,
                "fakulte_adi": str(row[15] or "?"),
                "donem": str(row[3] or ""),
                "status": str(row[4] or ""),
                "baslangic": row[5],
                "bitis": row[6],
                "sure_sn": _duration_seconds(row[5], row[6]),
                "ahp_profile_id": int(row[7]) if row[7] is not None else None,
                "ahp_profile_version": int(row[8]) if row[8] is not None else None,
                "ahp_weights": weights,
                "ahp_cr": float(row[10]) if row[10] is not None else None,
                "ahp_source": row[11],
                "ders_sayisi": ders_sayisi,
                "error_message": row[13],
                "stale": bool(row[14]) if row[14] is not None else False,
                # Hangi algoritmalar bu run'da calismis? decision_run icinde AHP+TOPSIS
                # her zaman calisir; trend ve ML opsiyonel — summary_json'dan bakilir.
                "algoritmalar": _detect_algorithms(summary),
            }
        )
    return out


def _detect_algorithms(summary: dict[str, Any]) -> list[str]:
    """summary_json'dan calismis algoritma kumesini cikar.

    AHP + TOPSIS her decision_run'da varsayilan olarak calisir; bunlari sabit kabul ederiz.
    Trend hep cagrilir (analyze_course_trend skor yolundan). ML (LR/RF/DT) advisory_ml
    olarak ayri calisir; summary'de varsa listeye eklenir.
    """
    algos = ["AHP", "TOPSIS", "Trend"]
    if not isinstance(summary, dict):
        return algos
    for key, label in (
        ("ml_lr_used", "LR"),
        ("ml_rf_used", "RF"),
        ("ml_dt_used", "DT"),
        ("lr_used", "LR"),
        ("rf_used", "RF"),
        ("dt_used", "DT"),
    ):
        if summary.get(key) and label not in algos:
            algos.append(label)
    return algos


def get_last_run_summary(
    conn: sqlite3.Connection,
    year: int | None = None,
    faculty_id: int | None = None,
) -> dict[str, Any] | None:
    """En son karar calistirmasini tek satirlik kullanici-ozeti olarak doner.

    UI'da "Son hesaplama" basligi icin kullanilir (Faz C toplu gorunum baslik satiri).
    """
    runs = get_recent_activity(conn, limit=1, year=year, faculty_id=faculty_id)
    if not runs:
        return None
    r = runs[0]
    sure = (
        f"{int(r['sure_sn'])} sn" if r.get("sure_sn") is not None else "—"
    )
    weights = r.get("ahp_weights") or {}
    ahp_info = (
        f"profil #{r['ahp_profile_id']} v{r.get('ahp_profile_version') or '?'}"
        if r.get("ahp_profile_id") is not None
        else "—"
    )
    return {
        **r,
        "ozet_metni": (
            f"Son: {r['baslangic']} | {r['fakulte_adi']} | yil={r['yil']} "
            f"donem={r['donem']} | durum={r['status']} | sure={sure} "
            f"| AHP={ahp_info} | dersler={r.get('ders_sayisi') or '—'} "
            f"| algoritmalar={', '.join(r.get('algoritmalar', []))}"
        ),
        "weights_compact": ", ".join(
            f"{k[:3]}={float(v):.3f}" for k, v in weights.items() if v is not None
        ) if isinstance(weights, dict) and weights else "—",
    }


def list_activity_for_year(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Yil bazli aktivite listesi (Algoritma Kontrol sayfasi icin)."""
    return get_recent_activity(conn, limit=limit, year=year, faculty_id=faculty_id)
