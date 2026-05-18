"""
Backward-compatible facade for reporting functions.

Yeni merkezi implementasyon: app.services.reporting_service
"""

from app.services.reporting_service import (  # noqa: F401
    build_report_snapshot,
    ensure_report_scores,
    fetch_curriculum_course_ids,
    normalize_term,
    status_label,
    term_key,
)
