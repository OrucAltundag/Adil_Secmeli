# -*- coding: utf-8 -*-
"""Dönem planı sürümleme + onay governance (§2.1 + §2.3).

AHP profil sürümlemesinin (`ahp_profile_policies.is_active`) dönem planlamaya
taşınmış hâli. Davranış:

- §2.1 Sürümleme: Aynı yıl+kapsam için tek **aktif** plan; alternatifleri
  aktifleştir/sil; başlıkta aktif planı göster.
- §2.3 Onay: Üretilen plan doğrudan müfredata yazılmaz; ``pending_review``
  kalır. Onaylanınca (``approved``) müfredata kaydedilebilir/aktifleştirilebilir;
  reddedilince hiçbir şey uygulanmaz.

Şema additive: ``semester_plan_runs`` tablosuna kolon EKLENİR (varsa atlanır);
mevcut akış (generate_semester_plan / list_plan_runs) etkilenmez.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

PENDING = "pending_review"
APPROVED = "approved"
REJECTED = "rejected"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_plan_governance_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='semester_plan_runs' LIMIT 1")
    if not cur.fetchone():
        return
    cols = {r[1] for r in cur.execute("PRAGMA table_info(semester_plan_runs)")}
    additions = [
        ("is_active", "ALTER TABLE semester_plan_runs ADD COLUMN is_active INTEGER DEFAULT 0"),
        ("decision_status", f"ALTER TABLE semester_plan_runs ADD COLUMN decision_status TEXT DEFAULT '{PENDING}'"),
        ("decided_by", "ALTER TABLE semester_plan_runs ADD COLUMN decided_by TEXT"),
        ("decided_at", "ALTER TABLE semester_plan_runs ADD COLUMN decided_at TEXT"),
        ("decision_reason", "ALTER TABLE semester_plan_runs ADD COLUMN decision_reason TEXT"),
    ]
    for name, ddl in additions:
        if name not in cols:
            cur.execute(ddl)


_SCOPE = "year = ? AND IFNULL(faculty_id, -1) = IFNULL(?, -1) AND IFNULL(department_id, -1) = IFNULL(?, -1)"


def set_plan_decision(
    conn: sqlite3.Connection,
    run_id: int,
    decision: str,
    user: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """§2.3: Planı onayla/reddet. Reddedilen plan aktiflikten düşer. Caller commit eder."""
    ensure_plan_governance_schema(conn)
    decision = str(decision).strip().lower()
    if decision not in (APPROVED, REJECTED, PENDING):
        return {"ok": False, "message": "Geçersiz karar."}
    cur = conn.cursor()
    cur.execute(
        "UPDATE semester_plan_runs SET decision_status=?, decided_by=?, decided_at=?, decision_reason=? WHERE id=?",
        (decision, user, _now(), reason, int(run_id)),
    )
    if decision != APPROVED:
        cur.execute("UPDATE semester_plan_runs SET is_active=0 WHERE id=?", (int(run_id),))
    if cur.rowcount == 0:
        return {"ok": False, "message": "Plan bulunamadı."}
    label = {APPROVED: "onaylandı", REJECTED: "reddedildi", PENDING: "beklemeye alındı"}[decision]
    return {"ok": True, "message": f"Plan {label}."}


def activate_plan_run(conn: sqlite3.Connection, run_id: int) -> dict[str, Any]:
    """§2.1: Bir planı aktif yap (yıl+kapsam için tek aktif). Yalnız onaylı plan aktive edilebilir."""
    ensure_plan_governance_schema(conn)
    cur = conn.cursor()
    row = cur.execute(
        "SELECT year, faculty_id, department_id, decision_status FROM semester_plan_runs WHERE id=?",
        (int(run_id),),
    ).fetchone()
    if not row:
        return {"ok": False, "message": "Plan bulunamadı."}
    if str(row[3] or "") != APPROVED:
        return {"ok": False, "message": "Önce planı onaylayın (yalnız onaylı plan aktifleştirilebilir)."}
    cur.execute(f"UPDATE semester_plan_runs SET is_active=0 WHERE {_SCOPE}", (row[0], row[1], row[2]))
    cur.execute("UPDATE semester_plan_runs SET is_active=1 WHERE id=?", (int(run_id),))
    return {"ok": True, "message": "Plan aktifleştirildi."}


def delete_plan_run(conn: sqlite3.Connection, run_id: int) -> dict[str, Any]:
    """§2.1: Aktif olmayan bir planı (ve atamalarını) siler. Caller commit eder."""
    ensure_plan_governance_schema(conn)
    cur = conn.cursor()
    row = cur.execute("SELECT is_active FROM semester_plan_runs WHERE id=?", (int(run_id),)).fetchone()
    if not row:
        return {"ok": False, "message": "Plan bulunamadı."}
    if int(row[0] or 0) == 1:
        return {"ok": False, "message": "Aktif plan silinemez. Önce başka bir planı aktifleştirin."}
    try:
        cur.execute("DELETE FROM semester_plan_course_assignments WHERE plan_run_id=?", (int(run_id),))
    except sqlite3.OperationalError:
        pass
    cur.execute("DELETE FROM semester_plan_runs WHERE id=?", (int(run_id),))
    return {"ok": True, "message": "Plan silindi."}


def get_active_plan(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None,
    department_id: int | None,
) -> dict[str, Any] | None:
    """§2.1: Yıl+kapsam için aktif planı döndürür (başlıkta göstermek için)."""
    ensure_plan_governance_schema(conn)
    cur = conn.cursor()
    row = cur.execute(
        f"SELECT id, run_name, plan_score, decision_status FROM semester_plan_runs "
        f"WHERE is_active=1 AND {_SCOPE} ORDER BY id DESC LIMIT 1",
        (int(year), faculty_id, department_id),
    ).fetchone()
    if not row:
        return None
    return {"id": int(row[0]), "run_name": row[1], "plan_score": row[2], "decision_status": row[3]}


def get_plan_decision_status(conn: sqlite3.Connection, run_id: int) -> dict[str, Any]:
    """Bir planın onay/aktiflik durumunu döndürür."""
    ensure_plan_governance_schema(conn)
    cur = conn.cursor()
    row = cur.execute(
        "SELECT decision_status, is_active FROM semester_plan_runs WHERE id=?", (int(run_id),)
    ).fetchone()
    if not row:
        return {"decision_status": None, "is_active": 0}
    return {"decision_status": row[0] or PENDING, "is_active": int(row[1] or 0)}
