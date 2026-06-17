# -*- coding: utf-8 -*-
"""Fakülte/bölüm bazlı dönemsel planlama taslağı üretici.

Spec (§8–§14) davranışı:

- §8  Kapsamın (fakülte/bölüm) **son müfredat yılı** bulunur; yeni planlama yılı
      otomatik olarak ``son yıl + 1`` olur.
- §9  Son yılın güz/bahar müfredatı kesinleşme puanlarıyla birlikte getirilir.
- §10 Hedef ders sayısı mevcuttan **fazla** ise: mevcut dersler korunur, eksik
      sayı kadar geçici (yer tutucu) ders başlığı (A, B, C…) eklenir. Bunlar
      gerçek ders olarak KAYDEDİLMEZ; yalnız taslakta görünür.
- §11 Hedef sayı **az** ise: en düşük kesinleşme puanlı derslerden başlanarak
      "müfredattan çıkarılması önerilen" olarak işaretlenir (silinmez).
- §13 Mevcut derslerin güz/bahar yerleşimi korunur; yer tutucular dengeli dağılır.
- §14 Kesinleşme puanı olmayan ders hata vermez; "manuel inceleme" kategorisine
      alınır ve otomatik çıkarmada en sona bırakılır.

Bu servis **yalnız taslak üretir** (salt-okunur); hiçbir şey yazmaz. Kullanıcı
onaylarsa mevcut "Planı Müfredata Kaydet" akışı kullanılır.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.curriculum_repository import (
    get_confirmation_scores_by_scope_and_year,
    get_curriculum_courses_by_year,
    get_latest_curriculum_year_by_faculty,
)
from app.services.course_curriculum_status_service import FALL, SPRING

# Durum jetonları
KEPT = "kept"
DROP_SUGGESTED = "drop_suggested"
ADDED_PLACEHOLDER = "added_placeholder"

# UI renkleri için durum -> renk jetonu (semester_planning_page _COLOR_TAGS ile uyumlu)
STATUS_COLOR = {
    KEPT: "green",
    DROP_SUGGESTED: "red",
    ADDED_PLACEHOLDER: "purple",
}

STATUS_LABEL = {
    KEPT: "Korunuyor",
    DROP_SUGGESTED: "Çıkarılması önerilen",
    ADDED_PLACEHOLDER: "Geçici yer tutucu",
}


def _placeholder_label(index: int) -> str:
    """0->A, 1->B, … 25->Z, 26->AA …"""
    label = ""
    n = index
    while True:
        label = chr(ord("A") + (n % 26)) + label
        n = n // 26 - 1
        if n < 0:
            break
    return label


def _load_scored_courses(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None,
    department_id: int | None,
) -> list[dict[str, Any]]:
    """Kapsam+yıl müfredat derslerini kesinleşme puanlarıyla birleştirir."""
    courses = get_curriculum_courses_by_year(conn, year, faculty_id, department_id)
    kp = get_confirmation_scores_by_scope_and_year(conn, year, faculty_id, department_id)
    seen: set[tuple[Any, str]] = set()
    out: list[dict[str, Any]] = []
    for c in courses:
        cid = c.get("course_id")
        term = c.get("term") or FALL
        key = (cid, term)
        if key in seen:
            continue
        seen.add(key)
        term_key = "b" if term == SPRING else "g"
        score = kp.get((int(cid), term_key)) if cid is not None else None
        out.append(
            {
                "course_id": cid,
                "course_code": c.get("course_code"),
                "course_name": c.get("course_name"),
                "term": term,
                "confirmation_score": score,  # None => kesinleşme puanı yok
            }
        )
    return out


def get_planning_scope_summary(
    conn: sqlite3.Connection,
    faculty_id: int | None,
    department_id: int | None = None,
) -> dict[str, Any]:
    """§8/§9: kapsam için son müfredat yılı, yeni planlama yılı ve mevcut müfredat özeti."""
    source_year = get_latest_curriculum_year_by_faculty(conn, faculty_id, department_id)
    if source_year is None:
        return {
            "ok": False,
            "source_year": None,
            "target_year": None,
            "current_count": 0,
            "fall_count": 0,
            "spring_count": 0,
            "courses": [],
            "message": "Seçili kapsam için mevcut müfredat bulunamadı.",
        }
    courses = _load_scored_courses(conn, source_year, faculty_id, department_id)
    fall = [c for c in courses if c["term"] == FALL]
    spring = [c for c in courses if c["term"] == SPRING]
    return {
        "ok": True,
        "source_year": source_year,
        "target_year": source_year + 1,
        "current_count": len(courses),
        "fall_count": len(fall),
        "spring_count": len(spring),
        "courses": courses,
        "message": "",
    }


def _kept_item(c: dict[str, Any]) -> dict[str, Any]:
    needs_review = c["confirmation_score"] is None
    return {
        "term": c["term"],
        "course_id": c["course_id"],
        "course_code": c["course_code"],
        "course_name": c["course_name"],
        "confirmation_score": c["confirmation_score"],
        "status": KEPT,
        "is_placeholder": False,
        "needs_manual_review": needs_review,
        "reason": (
            "Kesinleşme puanı bulunamadı (manuel inceleme)."
            if needs_review
            else "Mevcut müfredatta korunuyor."
        ),
    }


def _drop_item(c: dict[str, Any]) -> dict[str, Any]:
    score = c["confirmation_score"]
    return {
        "term": c["term"],
        "course_id": c["course_id"],
        "course_code": c["course_code"],
        "course_name": c["course_name"],
        "confirmation_score": score,
        "status": DROP_SUGGESTED,
        "is_placeholder": False,
        "needs_manual_review": score is None,
        "reason": (
            "Kesinleşme puanı yok; çıkarma için manuel inceleme."
            if score is None
            else f"En düşük kesinleşme puanlılardan ({score:.6f}); çıkarılması önerilir."
        ),
    }


def _placeholder_item(term: str, index: int) -> dict[str, Any]:
    label = _placeholder_label(index)
    return {
        "term": term,
        "course_id": None,
        "course_code": f"GECICI-{label}",
        "course_name": f"Geçici Ders {label} (havuzdan doldurulacak)",
        "confirmation_score": None,
        "status": ADDED_PLACEHOLDER,
        "is_placeholder": True,
        "needs_manual_review": False,
        "reason": "Hedef ders sayısı mevcuttan fazla; boş kontenjan / yer tutucu.",
    }


def _sort_key(item: dict[str, Any]) -> tuple[int, int, float]:
    # Güz önce, sonra bahar; durum: korunan < çıkarılan < yer tutucu; puan desc
    term_rank = 0 if item["term"] == FALL else 1
    status_rank = {KEPT: 0, DROP_SUGGESTED: 1, ADDED_PLACEHOLDER: 2}.get(item["status"], 3)
    score = item.get("confirmation_score")
    score_rank = -float(score) if isinstance(score, (int, float)) else 0.0
    return (term_rank, status_rank, score_rank)


def generate_planning_draft(
    conn: sqlite3.Connection,
    faculty_id: int | None,
    department_id: int | None = None,
    source_year: int | None = None,
    target_year: int | None = None,
    target_course_count: int | None = None,
) -> dict[str, Any]:
    """§10/§11/§13/§14: hedef ders sayısına göre planlama taslağı üretir (salt-okunur)."""
    summary = get_planning_scope_summary(conn, faculty_id, department_id)
    if not summary["ok"]:
        return {
            **summary,
            "items": [],
            "target_count": target_course_count or 0,
            "kept": 0,
            "added_placeholders": 0,
            "dropped": 0,
            "warnings": [],
        }

    sy = int(source_year) if source_year is not None else int(summary["source_year"])
    ty = int(target_year) if target_year is not None else int(summary["target_year"])
    courses: list[dict[str, Any]] = summary["courses"]
    current = len(courses)
    target = int(target_course_count) if target_course_count is not None else current
    target = max(0, target)

    items: list[dict[str, Any]] = []
    warnings: list[str] = []
    added = 0
    dropped = 0

    if target >= current:
        # Hepsini koru; fazlalık kadar yer tutucu ekle (§10, dengeli dağılım §13)
        for c in courses:
            items.append(_kept_item(c))
        need = target - current
        fall_n = sum(1 for c in courses if c["term"] == FALL)
        spring_n = sum(1 for c in courses if c["term"] == SPRING)
        for i in range(need):
            term = FALL if fall_n <= spring_n else SPRING
            if term == FALL:
                fall_n += 1
            else:
                spring_n += 1
            items.append(_placeholder_item(term, i))
        added = need
    else:
        # §11: en düşük kesinleşme puanlılardan çıkar; puansızlar en sona (§14)
        need_drop = current - target
        scored = [c for c in courses if c["confirmation_score"] is not None]
        unscored = [c for c in courses if c["confirmation_score"] is None]
        scored.sort(key=lambda c: c["confirmation_score"])  # artan: en düşük önce
        drop_list: list[dict[str, Any]] = []
        for c in scored:
            if len(drop_list) >= need_drop:
                break
            drop_list.append(c)
        if len(drop_list) < need_drop:
            remaining = need_drop - len(drop_list)
            drop_list.extend(unscored[:remaining])
            warnings.append(
                f"{remaining} dersin kesinleşme puanı yok; çıkarma için manuel inceleme önerilir."
            )
        drop_keys = {(c["course_id"], c["term"]) for c in drop_list}
        for c in courses:
            if (c["course_id"], c["term"]) in drop_keys:
                items.append(_drop_item(c))
                dropped += 1
            else:
                items.append(_kept_item(c))

    if any(it["needs_manual_review"] and it["status"] == KEPT for it in items):
        warnings.append("Bazı korunan derslerde kesinleşme puanı bulunamadı (manuel inceleme).")

    items.sort(key=_sort_key)
    kept = sum(1 for it in items if it["status"] == KEPT)

    fall_total = sum(1 for it in items if it["term"] == FALL and it["status"] != DROP_SUGGESTED)
    spring_total = sum(1 for it in items if it["term"] == SPRING and it["status"] != DROP_SUGGESTED)

    return {
        "ok": True,
        "source_year": sy,
        "target_year": ty,
        "current_count": current,
        "target_count": target,
        "fall_count": summary["fall_count"],
        "spring_count": summary["spring_count"],
        "fall_planned": fall_total,
        "spring_planned": spring_total,
        "items": items,
        "kept": kept,
        "added_placeholders": added,
        "dropped": dropped,
        "warnings": warnings,
        "message": _draft_message(current, target, added, dropped),
    }


def _draft_message(current: int, target: int, added: int, dropped: int) -> str:
    if target == current:
        return f"Hedef mevcut ders sayısına eşit ({current}); tüm dersler korunuyor."
    if target > current:
        return (
            f"Hedef ({target}) mevcuttan ({current}) fazla; {added} geçici yer tutucu eklendi."
        )
    return (
        f"Hedef ({target}) mevcuttan ({current}) az; en düşük kesinleşme puanlı "
        f"{dropped} dersin çıkarılması öneriliyor."
    )
