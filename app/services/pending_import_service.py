# -*- coding: utf-8 -*-
"""Onay kuyruğundaki staging importlarını canlı sisteme uygulama dağıtıcısı."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.services.criteria_import_service import apply_pending_criteria_import
from app.services.curriculum_import_service import apply_pending_curriculum_import
from app.services.import_audit_service import get_import_batch, reject_import
from app.services.import_staging_service import get_staged_payload, mark_staging_decision
from app.services.survey_import_service import apply_pending_survey_import


def apply_pending_import(
    conn: sqlite3.Connection,
    import_batch_id: int,
    user: str | None = None,
) -> dict[str, Any]:
    batch = get_import_batch(conn, int(import_batch_id))
    if not batch:
        return {"ok": False, "message": "Import kaydı bulunamadı."}
    status = str(batch.get("status") or "").lower()
    if status not in {"pending_review", "validated", "approved"}:
        return {"ok": False, "message": f"Bu import onay beklemiyor (durum: {status})."}
    import_type = str(batch.get("import_type") or "")
    if import_type == "criteria":
        return apply_pending_criteria_import(conn, int(import_batch_id), user=user)
    staged = get_staged_payload(conn, int(import_batch_id))
    if not staged or staged.get("staging_status") != "pending":
        return {"ok": False, "message": "Bu import için onay bekleyen staging verisi bulunamadı."}
    if import_type == "survey":
        return apply_pending_survey_import(conn, int(import_batch_id), user=user)
    if import_type == "curriculum":
        return apply_pending_curriculum_import(conn, int(import_batch_id), user=user)
    return {"ok": False, "message": f"Bu import türü staging onayını desteklemiyor: {import_type}"}


def reject_pending_import(
    conn: sqlite3.Connection,
    import_batch_id: int,
    reason: str,
    user: str | None = None,
) -> dict[str, Any]:
    batch = get_import_batch(conn, int(import_batch_id))
    if not batch:
        return {"ok": False, "message": "Import kaydı bulunamadı."}
    status = str(batch.get("status") or "").lower()
    if status not in {"pending_review", "validated", "approved"}:
        return {"ok": False, "message": f"Bu import onay beklemiyor (durum: {status})."}
    staged = get_staged_payload(conn, int(import_batch_id))
    import_type = str(batch.get("import_type") or "")
    if import_type != "criteria" and (not staged or staged.get("staging_status") != "pending"):
        return {"ok": False, "message": "Bu import için onay bekleyen staging verisi bulunamadı."}
    if staged and staged.get("staging_status") == "pending":
        mark_staging_decision(
            conn,
            int(import_batch_id),
            "rejected",
            user=user,
            note=reason,
        )
    result = reject_import(
        conn,
        int(import_batch_id),
        reason=reason,
        rejected_by=user,
    )
    return {"ok": True, "message": "Import reddedildi; canlı sisteme uygulanmadı.", **result}
