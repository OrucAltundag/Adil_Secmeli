# -*- coding: utf-8 -*-
"""Import kalite skoru hesaplama servisi."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_import_governance_schema
from app.services.import_audit_service import (
    get_import_batch,
    list_import_issues,
    list_import_rows,
)


QUALITY_MODEL_VERSION = "weighted_quality_v2_scope_aware"
QUALITY_WEIGHTS = {
    "matched_course_ratio": 0.25,
    "successful_row_ratio": 0.20,
    "valid_numeric_ratio": 0.20,
    "completeness_score": 0.15,
    "uniqueness_score": 0.10,
    "scope_consistency": 0.10,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


@dataclass
class ImportQualityResult:
    import_batch_id: int
    quality_score: float
    quality_level: str
    required_columns_ok: bool
    successful_row_ratio: float
    matched_course_ratio: float
    valid_numeric_ratio: float
    duplicate_row_count: int = 0
    unmatched_row_count: int = 0
    invalid_numeric_count: int = 0
    missing_required_count: int = 0
    out_of_range_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    summary: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def recommended_import_status(result: ImportQualityResult) -> str:
    """Kalite modeli ve sert kapılara göre kalıcı import durumunu döndürür."""
    summary = result.summary or {}
    status = str(summary.get("recommended_import_status") or "")
    if status in {"failed", "pending_review", "validated"}:
        return status
    return "pending_review" if result.quality_level == "low" else "validated"


def _quality_level(score: float) -> str:
    if score >= 0.80:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def evaluate_row_quality(row_result: dict[str, Any]) -> float:
    status = str(row_result.get("row_status") or "").lower()
    if status in {"matched", "applied", "ok", "success"}:
        return 1.0
    if status in {"skipped_override", "warning"}:
        return 0.65
    if row_result.get("matched_ders_id") is not None:
        return 0.75
    return 0.0


def evaluate_import_quality(conn: sqlite3.Connection, import_batch_id: int) -> ImportQualityResult:
    ensure_import_governance_schema(conn, commit=False)
    batch = get_import_batch(conn, int(import_batch_id))
    if not batch:
        raise ValueError("Import batch bulunamadi.")

    rows = list_import_rows(conn, int(import_batch_id), limit=100000)
    issues = list_import_issues(conn, int(import_batch_id), limit=100000)
    declared_row_count = int(batch.get("row_count") or 0)
    actual_row_count = len(rows)
    # Kalite hangi kapsam için hesaplanıyorsa payda o kapsamda gerçekten
    # denetlenen satır sayısıdır. Çok fakülteli dosyanın global metadata satır
    # sayısı fakülte batch'inin oranlarını yapay olarak düşürmemelidir.
    total_rows = actual_row_count if actual_row_count > 0 else max(declared_row_count, 1)
    excluded_by_scope_count = max(0, declared_row_count - actual_row_count) if actual_row_count else 0

    issue_type_counts: dict[str, int] = {}
    severity_counts: dict[str, int] = {}
    for issue in issues:
        issue_type_counts[str(issue.get("issue_type") or "unknown_error")] = (
            issue_type_counts.get(str(issue.get("issue_type") or "unknown_error"), 0) + 1
        )
        severity_counts[str(issue.get("severity") or "warning")] = (
            severity_counts.get(str(issue.get("severity") or "warning"), 0) + 1
        )

    matched_rows = 0
    successful_rows = 0
    row_hashes: list[str] = []
    for row in rows:
        if row.get("matched_ders_id") is not None:
            matched_rows += 1
        if evaluate_row_quality(row) >= 0.65:
            successful_rows += 1
        if row.get("row_hash"):
            row_hashes.append(str(row["row_hash"]))

    duplicate_row_count = max(0, len(row_hashes) - len(set(row_hashes)))
    unmatched_row_count = int(issue_type_counts.get("course_not_matched", 0))
    if rows and unmatched_row_count == 0:
        unmatched_row_count = max(0, len(rows) - matched_rows)

    invalid_numeric_count = int(issue_type_counts.get("invalid_numeric_value", 0))
    missing_required_count = int(issue_type_counts.get("missing_required_column", 0)) + int(
        issue_type_counts.get("empty_required_value", 0)
    )
    out_of_range_count = int(issue_type_counts.get("out_of_range", 0))
    warning_count = int(severity_counts.get("warning", 0))
    error_count = int(severity_counts.get("error", 0)) + int(severity_counts.get("critical", 0))

    required_columns_ok = missing_required_count == 0 and int(issue_type_counts.get("invalid_header", 0)) == 0
    successful_row_ratio = successful_rows / total_rows
    matched_course_ratio = matched_rows / total_rows if rows else (0.0 if declared_row_count else 1.0)
    valid_numeric_ratio = max(0.0, 1.0 - ((invalid_numeric_count + out_of_range_count) / total_rows))
    duplicate_penalty = min(1.0, duplicate_row_count / total_rows)
    scope_consistency = 0.0 if int(issue_type_counts.get("invalid_scope", 0)) else 1.0
    completeness_score = max(0.0, 1.0 - ((missing_required_count + unmatched_row_count) / total_rows))

    uniqueness_score = 1.0 - duplicate_penalty
    score = (
        QUALITY_WEIGHTS["matched_course_ratio"] * matched_course_ratio
        + QUALITY_WEIGHTS["successful_row_ratio"] * successful_row_ratio
        + QUALITY_WEIGHTS["valid_numeric_ratio"] * valid_numeric_ratio
        + QUALITY_WEIGHTS["completeness_score"] * completeness_score
        + QUALITY_WEIGHTS["uniqueness_score"] * uniqueness_score
        + QUALITY_WEIGHTS["scope_consistency"] * scope_consistency
    )

    # Sert doğrulama kapıları: yapısal/kapsamsal kritik hata, diğer iyi
    # bileşenlerle telafi edilip otomatik aktivasyona geçemez.
    invalid_header_count = int(issue_type_counts.get("invalid_header", 0))
    invalid_scope_count = int(issue_type_counts.get("invalid_scope", 0))
    numeric_fully_invalid = (invalid_numeric_count + out_of_range_count) >= total_rows
    if not required_columns_ok or invalid_header_count:
        hard_gate_status = "failed"
        hard_gate_reason = "Zorunlu kolon veya başlık doğrulaması başarısız."
    elif invalid_scope_count:
        hard_gate_status = "pending_review"
        hard_gate_reason = "Fakülte/bölüm/yıl kapsamı tutarsız."
    elif numeric_fully_invalid:
        hard_gate_status = "pending_review"
        hard_gate_reason = "Kapsamdaki sayısal değerlerin tamamı geçersiz veya aralık dışında."
    else:
        hard_gate_status = "passed"
        hard_gate_reason = None
    if hard_gate_status != "passed":
        score = min(score, 0.5499)
    score = max(0.0, min(1.0, round(score, 4)))
    level = _quality_level(score)
    summary = {
        "row_count": total_rows,
        "actual_row_count": actual_row_count,
        "declared_file_row_count": declared_row_count,
        "excluded_by_scope_count": excluded_by_scope_count,
        "issue_type_counts": issue_type_counts,
        "severity_counts": severity_counts,
        "required_columns_ok": required_columns_ok,
        "quality_level": level,
        "quality_model_name": "Ağırlıklı Teknik Import Kalitesi",
        "quality_model_version": QUALITY_MODEL_VERSION,
        "quality_weights": QUALITY_WEIGHTS,
        "hard_gate_status": hard_gate_status,
        "hard_gate_reason": hard_gate_reason,
        "recommended_import_status": (
            hard_gate_status if hard_gate_status != "passed"
            else ("pending_review" if level == "low" else "validated")
        ),
    }

    result = ImportQualityResult(
        import_batch_id=int(import_batch_id),
        quality_score=score,
        quality_level=level,
        required_columns_ok=required_columns_ok,
        successful_row_ratio=round(successful_row_ratio, 4),
        matched_course_ratio=round(matched_course_ratio, 4),
        valid_numeric_ratio=round(valid_numeric_ratio, 4),
        duplicate_row_count=duplicate_row_count,
        unmatched_row_count=unmatched_row_count,
        invalid_numeric_count=invalid_numeric_count,
        missing_required_count=missing_required_count,
        out_of_range_count=out_of_range_count,
        warning_count=warning_count,
        error_count=error_count,
        summary=summary,
    )

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO import_quality_checks (
            import_batch_id, quality_score, quality_level, required_columns_ok,
            successful_row_ratio, matched_course_ratio, valid_numeric_ratio,
            duplicate_row_count, unmatched_row_count, invalid_numeric_count,
            missing_required_count, out_of_range_count, warning_count, error_count,
            summary_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result.import_batch_id,
            result.quality_score,
            result.quality_level,
            1 if result.required_columns_ok else 0,
            result.successful_row_ratio,
            result.matched_course_ratio,
            result.valid_numeric_ratio,
            result.duplicate_row_count,
            result.unmatched_row_count,
            result.invalid_numeric_count,
            result.missing_required_count,
            result.out_of_range_count,
            result.warning_count,
            result.error_count,
            _json_dumps(summary),
            _now(),
        ),
    )
    cur.execute(
        """
        UPDATE import_batches
        SET quality_score = ?, quality_level = ?, updated_at = ?
        WHERE id = ?
        """,
        (result.quality_score, result.quality_level, _now(), int(import_batch_id)),
    )

    source_table = batch.get("source_table")
    source_import_id = batch.get("source_import_id")
    if source_table and source_import_id is not None:
        try:
            cur.execute(
                f"UPDATE {source_table} SET quality_score = ?, quality_level = ? WHERE import_id = ?",
                (result.quality_score, result.quality_level, int(source_import_id)),
            )
        except sqlite3.DatabaseError:
            pass

    return result


def summarize_quality(conn: sqlite3.Connection, import_batch_id: int) -> dict[str, Any]:
    ensure_import_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM import_quality_checks
        WHERE import_batch_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (int(import_batch_id),),
    )
    row = cur.fetchone()
    if not row:
        return evaluate_import_quality(conn, int(import_batch_id)).as_dict()
    if isinstance(row, sqlite3.Row):
        data = {key: row[key] for key in row.keys()}
    else:
        cols = [desc[0] for desc in cur.description]
        data = {cols[idx]: row[idx] for idx in range(len(cols))}
    try:
        data["summary"] = json.loads(data.get("summary_json") or "{}")
    except Exception:
        data["summary"] = {}
    if data["summary"].get("quality_model_version") != QUALITY_MODEL_VERSION:
        refreshed = evaluate_import_quality(conn, int(import_batch_id)).as_dict()
        conn.commit()
        return refreshed
    return data
