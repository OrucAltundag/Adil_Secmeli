# -*- coding: utf-8 -*-
"""Mimari kalite sağlık kontrolleri."""

from __future__ import annotations

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _ArchCheck(BaseHealthCheck):
    category = "Mimari"
    score_bucket = "architecture"


class LayerViolationCheck(_ArchCheck):
    name = "Katman ihlali kontrolü (UI doğrudan DB)"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        from app.services.architecture_audit_service import (
            generate_architecture_audit_report,
        )

        report = generate_architecture_audit_report()
        ui_findings = [
            item
            for item in (report.get("groups") or {}).get("ui_direct_db_access", [])
        ]
        violations = [f for f in ui_findings if not f.get("allowlisted")]
        watched = [f for f in ui_findings if f.get("allowlisted")]
        if violations:
            detail = "\n".join(
                f"- {f['file']}:{f.get('line')} ({f.get('pattern')})"
                for f in violations[:20]
            )
            return self.warning(
                "UI katmanında doğrudan SQLite erişimi var.",
                detail="İhlaller:\n" + detail,
                suggestion="DB işlemlerini service/repository katmanına taşıyın.",
                metadata={"violation_count": len(violations)},
            )
        if watched:
            detail = "\n".join(
                f"- {f['file']}:{f.get('line')} | {f.get('allowlist_reason')}"
                for f in watched[:20]
            )
            return self.info(
                "UI'da yalnızca allowlist kapsamında izlenen DB erişimi var.",
                detail="İzlenen geçiş kalemleri:\n" + detail,
                suggestion="Aşamalı refactor planına göre service katmanına taşıyın.",
                metadata={"watched_count": len(watched)},
            )
        return self.ok(
            "UI katmanında doğrudan DB erişimi bulgusu yok.",
            detail="Mimari sınır ihlali tespit edilmedi.",
        )


class CircularImportCheck(_ArchCheck):
    name = "Döngüsel import kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        targets = [
            "app.services.system_service",
            "app.services.health_service",
            "app.services.service_factory",
            "app.health.health_runner",
        ]
        failed: list[str] = []
        import importlib

        for module in targets:
            try:
                importlib.import_module(module)
            except ImportError as exc:
                if "circular" in str(exc).lower() or "partially initialized" in str(exc).lower():
                    failed.append(f"- {module}: {exc}")
            except Exception:  # noqa: BLE001 - diğer hatalar bu kontrolün konusu değil
                continue
        if failed:
            return self.warning(
                "Olası döngüsel import tespit edildi.",
                detail="\n".join(failed),
                suggestion="İlgili modüllerde import'ları fonksiyon içine alın.",
            )
        return self.ok(
            "Temel modüllerde döngüsel import tespit edilmedi.",
            detail=f"Kontrol edilen modül: {len(targets)}",
        )


class DuplicateCodeHintCheck(_ArchCheck):
    name = "Yinelenen DB bağlantı yardımcı kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        root = context.root / "app"
        hits: list[str] = []
        needles = ("def connect_sqlite", "def open_sqlite_connection")
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:  # noqa: BLE001
                continue
            for needle in needles:
                if needle in text:
                    hits.append(f"- {path.relative_to(context.root).as_posix()}: {needle}")
        defs = [h for h in hits]
        if len(defs) > 2:
            return self.info(
                "Birden fazla DB bağlantı yardımcı tanımı var.",
                detail="\n".join(defs),
                suggestion="Bağlantı yardımcılarını tek modülde toplamayı değerlendirin.",
                metadata={"count": len(defs)},
            )
        return self.ok(
            "DB bağlantı yardımcıları merkezi (yinelenme düşük).",
            detail=f"Tespit edilen tanım: {len(defs)}",
        )


class DeadCodeHintCheck(_ArchCheck):
    name = "Ölü kod ipucu (registry_temp)"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        suspects: list[str] = []
        for path in (context.root / "app").rglob("*_temp.py"):
            if "__pycache__" in path.parts:
                continue
            suspects.append(path.relative_to(context.root).as_posix())
        if suspects:
            return self.info(
                "Geçici/olası ölü kod dosyaları var.",
                detail="\n".join(f"- {s}" for s in suspects),
                suggestion="Kullanılmıyorsa temizleyin; emin değilseniz koruyun.",
                metadata={"suspects": suspects},
            )
        return self.ok(
            "Belirgin geçici/ölü kod dosyası bulunamadı.",
            detail="*_temp.py kalıbı taranmıştır.",
        )


class ServiceLayerCheck(_ArchCheck):
    name = "Servis/repository katmanı kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        services = context.root / "app" / "services"
        repos = context.root / "app" / "repositories"
        missing = [
            name
            for name, p in (("app/services", services), ("app/repositories", repos))
            if not p.exists()
        ]
        if missing:
            return self.warning(
                "Servis/repository katmanı eksik.",
                detail="Eksik: " + ", ".join(missing),
                suggestion="İş kuralları için servis, sorgular için repository ekleyin.",
            )
        return self.ok(
            "Servis ve repository katmanları mevcut.",
            detail="app/services ve app/repositories bulundu.",
        )
