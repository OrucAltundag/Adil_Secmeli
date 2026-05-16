# -*- coding: utf-8 -*-
"""Yedekleme sağlık kontrolleri."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import time
from pathlib import Path

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _BackupCheck(BaseHealthCheck):
    category = "Yedekleme"
    score_bucket = "architecture"


class BackupDirectoryCheck(_BackupCheck):
    name = "Yedek dizini kontrolü"
    quick = True
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        path = context.health_config.backups_path()
        if path.exists():
            backups = list(path.glob("*.db")) + list(path.glob("*.sqlite*"))
            return self.ok(
                f"Yedek dizini mevcut ({len(backups)} yedek).",
                detail=str(path),
                metadata={"backup_count": len(backups)},
            )
        try:
            path.mkdir(parents=True, exist_ok=True)
            return self.info(
                "Yedek dizini yoktu, oluşturuldu.",
                detail=str(path),
                suggestion="Periyodik yedek almayı planlayın.",
            )
        except Exception as exc:  # noqa: BLE001
            return self.warning(
                "Yedek dizini oluşturulamadı.",
                detail=f"{type(exc).__name__}: {exc} ({path})",
                suggestion="Yazılabilir bir yedek klasörü tanımlayın.",
            )


class BackupCreateCheck(_BackupCheck):
    name = "Yedek alma kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        if not context.database.is_sqlite():
            return self.skipped(
                "SQLite dışı backend; dosya yedeği atlandı.",
                detail=f"database_url={context.app_config.database_url}",
                suggestion="PostgreSQL için pg_dump tabanlı yedek kullanın.",
            )
        db_path = context.db_path or ""
        if not os.path.exists(db_path):
            return self.warning(
                "Yedeklenecek veritabanı bulunamadı.",
                detail=f"DB yolu yok: {db_path}",
                suggestion="DB dosyasının varlığını kontrol edin.",
            )
        tmp_dir = tempfile.mkdtemp(prefix="health_backup_")
        target = Path(tmp_dir) / "probe_backup.db"
        try:
            with context.database.connection() as source:
                dest = sqlite3.connect(str(target))
                try:
                    source.backup(dest)
                finally:
                    dest.close()
            ok = target.exists() and target.stat().st_size > 0
        except Exception as exc:  # noqa: BLE001
            return self.warning(
                "Veritabanı yedeği alınamadı.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="Disk alanı ve izinleri kontrol edin.",
            )
        finally:
            try:
                if target.exists():
                    target.unlink()
                os.rmdir(tmp_dir)
            except Exception:
                pass
        if not ok:
            return self.warning(
                "Yedek dosyası boş üretildi.",
                detail="Kopyalanan dosya boyutu 0.",
                suggestion="Kaynak DB ve disk durumunu kontrol edin.",
            )
        return self.ok(
            "Veritabanının güvenli kopyası alınabiliyor.",
            detail="Geçici hedefe yedek alındı ve temizlendi (gerçek veri korundu).",
        )


class BackupReadCheck(_BackupCheck):
    name = "Yedek okunabilirlik kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        path = context.health_config.backups_path()
        if not path.exists():
            return self.info(
                "Yedek dizini yok; okuma testi atlandı.",
                detail=str(path),
                suggestion="Önce yedek dizinini/yedeği oluşturun.",
            )
        backups = sorted(
            list(path.glob("*.db")) + list(path.glob("*.sqlite*")),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not backups:
            return self.info(
                "Mevcut yedek bulunamadı.",
                detail=str(path),
                suggestion="Düzenli yedek alın.",
            )
        latest = backups[0]
        try:
            conn = sqlite3.connect(f"file:{latest}?mode=ro", uri=True)
            try:
                conn.execute(
                    "SELECT COUNT(*) FROM sqlite_master"
                ).fetchone()
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001
            return self.warning(
                "En son yedek okunamadı.",
                detail=f"{latest.name}: {type(exc).__name__}: {exc}",
                suggestion="Yedek dosyası bozulmuş olabilir; yeni yedek alın.",
            )
        return self.ok(
            "En son yedek okunabiliyor.",
            detail=f"Doğrulanan yedek: {latest.name}",
            metadata={"latest_backup": latest.name},
        )


class BackupAgeCheck(_BackupCheck):
    name = "Yedek tazeliği kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        path = context.health_config.backups_path()
        backups = (
            sorted(
                list(path.glob("*.db")) + list(path.glob("*.sqlite*")),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if path.exists()
            else []
        )
        if not backups:
            return self.info(
                "Hiç yedek yok; tazelik değerlendirilemiyor.",
                detail=str(path),
                suggestion="Düzenli yedek almayı planlayın.",
            )
        latest = backups[0]
        age_days = (time.time() - latest.stat().st_mtime) / 86400.0
        max_age = context.health_config.backup_max_age_days
        if age_days > max_age:
            return self.warning(
                f"Son yedek çok eski ({age_days:.1f} gün).",
                detail=f"{latest.name} • eşik {max_age} gün",
                suggestion="Güncel bir yedek alın.",
                metadata={"age_days": round(age_days, 1)},
            )
        return self.ok(
            f"Son yedek güncel ({age_days:.1f} gün).",
            detail=f"{latest.name} • eşik {max_age} gün",
            metadata={"age_days": round(age_days, 1)},
        )
