# -*- coding: utf-8 -*-
"""Veritabanı sağlık kontrolleri (bağlantı, bütünlük, FK, tablo, yazma)."""

from __future__ import annotations

import os
import time

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _DatabaseCheck(BaseHealthCheck):
    category = "Veritabanı"
    score_bucket = "database"

    def _skip_if_not_sqlite(self, context: HealthContext) -> HealthCheckResult | None:
        if not context.database.is_sqlite():
            return self.skipped(
                "SQLite dışı backend; bu kontrol atlandı.",
                detail=f"database_url={context.app_config.database_url}",
                suggestion="PostgreSQL kullanılıyorsa ilgili DBA araçlarını kullanın.",
            )
        return None


class SQLiteConnectionCheck(_DatabaseCheck):
    name = "SQLite bağlantı kontrolü"
    quick = True
    default_severity = HealthSeverity.CRITICAL

    def run(self, context: HealthContext) -> HealthCheckResult:
        skip = self._skip_if_not_sqlite(context)
        if skip:
            return skip
        db_path = context.db_path or ""
        if not os.path.exists(db_path):
            return self.critical(
                "Veritabanına bağlanılamadı.",
                detail=f"Veritabanı dosyası bulunamadı: {db_path}",
                suggestion="DB dosyasının varlığını ve config.json yolunu kontrol edin.",
                metadata={"db_path": db_path},
            )
        start = time.perf_counter()
        with context.repository() as repo:
            ok = repo.scalar("SELECT 1") == 1
        elapsed = (time.perf_counter() - start) * 1000.0
        if not ok:
            return self.critical(
                "Veritabanı bağlantısı doğrulanamadı.",
                detail="SELECT 1 beklenen sonucu döndürmedi.",
                suggestion="Veritabanı dosyasının bozuk olmadığını kontrol edin.",
            )
        return self.ok(
            "Veritabanı bağlantısı başarılı.",
            detail=f"{db_path}\nBağlantı + ping süresi: {elapsed:.1f} ms",
            metadata={"db_path": db_path, "connect_ms": round(elapsed, 1)},
        )


class SQLiteIntegrityCheck(_DatabaseCheck):
    name = "SQLite bütünlük kontrolü"
    default_severity = HealthSeverity.CRITICAL

    def run(self, context: HealthContext) -> HealthCheckResult:
        skip = self._skip_if_not_sqlite(context)
        if skip:
            return skip
        with context.repository() as repo:
            rows = repo.integrity_check()
        if rows == ["ok"]:
            return self.ok(
                "Veritabanı bütünlük kontrolü başarılı.",
                detail="PRAGMA integrity_check sonucu: ok",
            )
        detail = "PRAGMA integrity_check sonucu:\n" + "\n".join(rows[:20])
        return self.critical(
            "Veritabanı bütünlük kontrolü başarısız.",
            detail=detail,
            suggestion="Veritabanı yedeği alınmalı ve bozuk tablo incelenmelidir.",
            metadata={"issues": rows[:20]},
        )


class SQLiteForeignKeyCheck(_DatabaseCheck):
    name = "SQLite yabancı anahtar kontrolü"
    default_severity = HealthSeverity.HIGH

    def run(self, context: HealthContext) -> HealthCheckResult:
        skip = self._skip_if_not_sqlite(context)
        if skip:
            return skip
        with context.repository() as repo:
            violations = repo.foreign_key_check()
        if not violations:
            return self.ok(
                "Yabancı anahtar tutarlılığı sağlanıyor.",
                detail="PRAGMA foreign_key_check ihlal bulmadı.",
            )
        sample = "\n".join(
            f"- tablo={v[0]} rowid={v[1]} hedef={v[2]}" for v in violations[:15]
        )
        status = self.critical if len(violations) > 50 else self.warning
        return status(
            "Yabancı anahtar tutarsızlıkları bulundu.",
            detail=f"Toplam ihlal: {len(violations)}\n{sample}",
            suggestion="Yetim/eşleşmeyen kayıtları ilgili tablolarda düzeltin.",
            metadata={"violation_count": len(violations)},
        )


class SQLiteTableCountCheck(_DatabaseCheck):
    name = "SQLite tablo sayısı kontrolü"
    quick = True
    default_severity = HealthSeverity.HIGH

    def run(self, context: HealthContext) -> HealthCheckResult:
        skip = self._skip_if_not_sqlite(context)
        if skip:
            return skip
        with context.repository() as repo:
            count = repo.table_count()
        minimum = context.health_config.min_table_count
        if count == 0:
            return self.critical(
                "Veritabanında hiç tablo yok.",
                detail="sqlite_master içinde kullanıcı tablosu bulunamadı.",
                suggestion="Şema migrasyonunu çalıştırın (python -m app.main --mode migrate).",
                metadata={"table_count": 0},
            )
        if count < minimum:
            return self.warning(
                f"Tablo sayısı beklenenden az ({count} < {minimum}).",
                detail=f"Mevcut tablo sayısı: {count}",
                suggestion="Migrasyon/şema uyumluluğunun tamamlandığını doğrulayın.",
                metadata={"table_count": count, "min": minimum},
            )
        return self.ok(
            f"Tablo sayısı yeterli ({count}).",
            detail=f"Mevcut tablo sayısı: {count} (min {minimum})",
            metadata={"table_count": count},
        )


class SQLiteWritePermissionCheck(_DatabaseCheck):
    name = "SQLite yazma izni kontrolü"
    default_severity = HealthSeverity.HIGH

    def run(self, context: HealthContext) -> HealthCheckResult:
        skip = self._skip_if_not_sqlite(context)
        if skip:
            return skip
        # Gerçek veriyi bozmamak için TEMP tablo kullanılır; commit edilmez.
        with context.database.connection() as conn:
            try:
                conn.execute(
                    "CREATE TEMP TABLE _health_write_probe (id INTEGER PRIMARY KEY, v TEXT)"
                )
                conn.execute("INSERT INTO _health_write_probe (v) VALUES ('probe')")
                value = conn.execute(
                    "SELECT v FROM _health_write_probe LIMIT 1"
                ).fetchone()[0]
                conn.execute("DROP TABLE _health_write_probe")
                conn.rollback()
            except Exception as exc:  # noqa: BLE001
                return self.warning(
                    "Veritabanına yazma izni doğrulanamadı.",
                    detail=f"{type(exc).__name__}: {exc}",
                    suggestion="DB dosyası ve klasörü için yazma izni olduğundan emin olun.",
                )
        if value != "probe":
            return self.warning(
                "Yazma testi beklenen değeri döndürmedi.",
                detail=f"Beklenen 'probe', dönen '{value}'.",
                suggestion="Veritabanı dosyasını ve diski kontrol edin.",
            )
        return self.ok(
            "Veritabanı yazılabilir (TEMP tablo testi, rollback edildi).",
            detail="Gerçek veri değiştirilmedi; geçici tablo kullanıldı.",
        )
