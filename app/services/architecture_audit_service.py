# -*- coding: utf-8 -*-
"""Mimari sınır ihlallerini görünür hale getiren tarama servisi."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]

UI_DB_ALLOWLIST = {
    "app/ui/tabs/view_tab.py": "Admin tablo görüntüleyici ve SQL Console",
    "app/ui/tabs/data_management_page.py": "Import governance geçiş ekranı; servis katmanına aşamalı taşınıyor",
}

API_RAW_SQL_ALLOWLIST = {
    "app/api/routes.py": "Legacy API route dosyası; yeni endpointler service adapter standardına geçiriliyor",
}

SERVICE_SQLITE_ALLOWLIST = {
    "app/services/db.py": "Legacy DB helper",
    "app/services/report_table_service.py": "Admin tablo görüntüleme servisi repository arkasında çalışır",
    "app/services/system_service.py": "Sistem sağlığı için merkezi adapter",
    "app/services/database_service.py": "Sağlık merkezi için sanctioned DB erişim adapteri (repository arkasında, context-managed)",
}

SCHEMA_MUTATION_ALLOWLIST_PREFIXES = {
    "app/db/schema_compat.py",
    "app/db/sqlite_db.py",
    "app/etl/",
    "app/scripts/",
    "alembic/versions/",
}


@dataclass
class ArchitectureFinding:
    layer: str
    file: str
    line: int
    pattern: str
    severity: str
    allowlisted: bool
    allowlist_reason: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _iter_py_files(relative_dir: str) -> Iterable[Path]:
    root = ROOT / relative_dir
    if not root.exists():
        return []
    return (path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _scan_patterns(
    relative_dir: str,
    patterns: tuple[str, ...],
    *,
    layer: str,
    allowlist: dict[str, str] | None = None,
    severity: str = "warning",
) -> list[ArchitectureFinding]:
    findings: list[ArchitectureFinding] = []
    allowlist = allowlist or {}
    for path in _iter_py_files(relative_dir):
        rel = _relative(path)
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern in patterns:
                if pattern.lower() not in line.lower():
                    continue
                reason = allowlist.get(rel, "")
                findings.append(
                    ArchitectureFinding(
                        layer=layer,
                        file=rel,
                        line=line_number,
                        pattern=pattern,
                        severity=("info" if reason else severity),
                        allowlisted=bool(reason),
                        allowlist_reason=reason,
                        message=(
                            "Allowlist kapsamında izlenen legacy kullanım."
                            if reason
                            else "Repository/service sınırına taşınması gereken kullanım."
                        ),
                    )
                )
    return findings


def scan_ui_direct_db_access() -> list[dict[str, Any]]:
    patterns = ("sqlite3.connect", "connect_sqlite", "open_sqlite_connection", "cursor.execute", "conn.execute")
    return [item.to_dict() for item in _scan_patterns("app/ui", patterns, layer="ui", allowlist=UI_DB_ALLOWLIST)]


def scan_api_raw_sql() -> list[dict[str, Any]]:
    patterns = ("sqlite3.connect", "cursor.execute", "conn.execute", "SELECT ", "INSERT ", "UPDATE ", "DELETE ")
    return [item.to_dict() for item in _scan_patterns("app/api", patterns, layer="api", allowlist=API_RAW_SQL_ALLOWLIST)]


def scan_service_sqlite_usage() -> list[dict[str, Any]]:
    patterns = ("sqlite3.connect", "connect_sqlite", "cursor.execute", "conn.execute")
    return [
        item.to_dict()
        for item in _scan_patterns("app/services", patterns, layer="service", allowlist=SERVICE_SQLITE_ALLOWLIST)
    ]


def scan_schema_mutation_usage() -> list[dict[str, Any]]:
    patterns = ("ALTER TABLE", "CREATE TABLE", "DROP TABLE")
    raw = _scan_patterns("app", patterns, layer="schema", allowlist={}, severity="error")
    findings: list[dict[str, Any]] = []
    for item in raw:
        allowed = any(item.file.startswith(prefix) for prefix in SCHEMA_MUTATION_ALLOWLIST_PREFIXES)
        item.allowlisted = allowed
        item.allowlist_reason = "Schema compatibility veya Alembic migration alanı" if allowed else ""
        item.severity = "info" if allowed else "error"
        item.message = (
            "İzinli schema yönetim alanı."
            if allowed
            else "Runtime schema mutation schema_compat veya Alembic dışında tespit edildi."
        )
        findings.append(item.to_dict())
    return findings


def generate_architecture_audit_report() -> dict[str, Any]:
    groups = {
        "ui_direct_db_access": scan_ui_direct_db_access(),
        "api_raw_sql": scan_api_raw_sql(),
        "service_sqlite_usage": scan_service_sqlite_usage(),
        "schema_mutation_usage": scan_schema_mutation_usage(),
    }
    all_findings = [finding for items in groups.values() for finding in items]
    violations = [finding for finding in all_findings if not finding.get("allowlisted")]
    return {
        "ok": not violations,
        "violation_count": len(violations),
        "finding_count": len(all_findings),
        "groups": groups,
        "recommendations": [
            "Yeni UI/API kodunda doğrudan DB erişimi eklemeyin.",
            "Yeni sorguları repository katmanına, iş kurallarını service katmanına taşıyın.",
            "schema_compat sadece legacy SQLite uyumluluğu için kullanılmalıdır.",
        ],
    }


def export_architecture_audit_report(format: str = "json") -> str:
    report = generate_architecture_audit_report()
    if format == "csv":
        rows = [finding for items in report["groups"].values() for finding in items]
        if not rows:
            return ""
        import io

        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return buffer.getvalue()
    if format == "txt":
        lines = [f"Bulgu: {report['finding_count']}", f"İhlal: {report['violation_count']}"]
        for group_name, findings in report["groups"].items():
            lines.append(f"[{group_name}] {len(findings)} bulgu")
        return "\n".join(lines)
    return json.dumps(report, ensure_ascii=False, indent=2)
