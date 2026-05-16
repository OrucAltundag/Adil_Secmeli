# -*- coding: utf-8 -*-
"""SQLite veritabanı sağlık kontrolleri."""

from __future__ import annotations

from pathlib import Path

from app.health.checks.base_check import BaseHealthCheck
from app.health.health_config import EXPECTED_MIN_TABLE_COUNT
from app.health.models import HealthContext, HealthSeverity, HealthStatus
from app.repositories.sqlite_repository import SQLiteRepository


class SQLiteConnectionCheck(BaseHealthCheck):
    name = "SQLite bağlantı kontrolü"
    category = "Veritabanı Sağlığı"
    severity = HealthSeverity.CRITICAL.value
    source = "app.health.checks.database_check.SQLiteConnectionCheck"
    quick = True

    def run(self, context: HealthContext):
        db_path = Path(context.db_path)
        if not db_path.exists():
            return self.result(
                HealthStatus.CRITICAL,
                "Veritabanı dosyası bulunamadı.",
                severity=HealthSeverity.CRITICAL,
                detail=str(db_path),
                suggestion="DB dosyasının varlığını ve config.json içindeki db_path değerini kontrol edin.",
            )
        repo = SQLiteRepository(str(db_path))
        value = repo.execute_scalar("SELECT 1")
        if value == 1:
            return self.result(
                HealthStatus.OK,
                "Veritabanı bağlantısı başarılı.",
                detail=str(db_path),
                metadata={"db_path": str(db_path)},
            )
        return self.result(
            HealthStatus.CRITICAL,
            "Veritabanına bağlanıldı ancak test sorgusu beklenen sonucu dönmedi.",
            severity=HealthSeverity.CRITICAL,
            detail=f"SELECT 1 sonucu: {value}",
            suggestion="SQLite dosyasını ve bağlantı adapterını kontrol edin.",
        )


class SQLiteIntegrityCheck(BaseHealthCheck):
    name = "SQLite bütünlük kontrolü"
    category = "Veritabanı Sağlığı"
    severity = HealthSeverity.CRITICAL.value
    source = "app.health.checks.database_check.SQLiteIntegrityCheck"

    def run(self, context: HealthContext):
        rows = SQLiteRepository(context.db_path).integrity_check()
        if rows == ["ok"]:
            return self.result(HealthStatus.OK, "Veritabanı bütünlük kontrolü başarılı.", detail="PRAGMA integrity_check: ok")
        return self.result(
            HealthStatus.CRITICAL,
            "Veritabanı bütünlük kontrolü başarısız.",
            severity=HealthSeverity.CRITICAL,
            detail="; ".join(rows[:20]),
            suggestion="Veritabanı yedeği alınmalı ve bozuk tablo/kayıt incelenmeli.",
            metadata={"integrity_rows": rows},
        )


class SQLiteForeignKeyCheck(BaseHealthCheck):
    name = "SQLite foreign key kontrolü"
    category = "Veritabanı Sağlığı"
    severity = HealthSeverity.HIGH.value
    source = "app.health.checks.database_check.SQLiteForeignKeyCheck"

    def run(self, context: HealthContext):
        issues = SQLiteRepository(context.db_path).foreign_key_check()
        if not issues:
            return self.result(HealthStatus.OK, "Foreign key kontrolünde ihlal bulunmadı.", detail="PRAGMA foreign_key_check boş döndü.")
        status = HealthStatus.CRITICAL if len(issues) > 20 else HealthStatus.WARNING
        return self.result(
            status,
            "Foreign key ilişki ihlalleri bulundu.",
            severity=HealthSeverity.HIGH,
            detail=f"İhlal sayısı: {len(issues)}",
            suggestion="İlgili tablo ve kayıtları inceleyip yetim kayıtları düzeltin.",
            metadata={"issues": issues[:50]},
        )


class SQLiteTableCountCheck(BaseHealthCheck):
    name = "SQLite tablo sayısı kontrolü"
    category = "Veritabanı Sağlığı"
    severity = HealthSeverity.HIGH.value
    source = "app.health.checks.database_check.SQLiteTableCountCheck"
    quick = True

    def run(self, context: HealthContext):
        count = SQLiteRepository(context.db_path).table_count()
        if count <= 0:
            return self.result(
                HealthStatus.CRITICAL,
                "Veritabanında tablo bulunamadı.",
                severity=HealthSeverity.CRITICAL,
                suggestion="Schema/migration adımlarını çalıştırın.",
                metadata={"table_count": count},
            )
        if count < EXPECTED_MIN_TABLE_COUNT:
            return self.result(
                HealthStatus.WARNING,
                "Tablo sayısı beklenen minimum değerin altında.",
                severity=HealthSeverity.MEDIUM,
                detail=f"Tablo sayısı: {count}, beklenen minimum: {EXPECTED_MIN_TABLE_COUNT}",
                suggestion="Eksik migration veya yanlış DB dosyası kullanımı olasılığını kontrol edin.",
                metadata={"table_count": count},
            )
        return self.result(
            HealthStatus.OK,
            "Veritabanı tablo sayısı beklenen aralıkta.",
            detail=f"Tablo sayısı: {count}",
            metadata={"table_count": count},
        )


class SQLiteWritePermissionCheck(BaseHealthCheck):
    name = "SQLite yazma yetkisi kontrolü"
    category = "Veritabanı Sağlığı"
    severity = HealthSeverity.HIGH.value
    source = "app.health.checks.database_check.SQLiteWritePermissionCheck"

    def run(self, context: HealthContext):
        SQLiteRepository(context.db_path).write_permission_check()
        return self.result(
            HealthStatus.OK,
            "Veritabanı yazma yetkisi güvenli transaction testiyle doğrulandı.",
            detail="Geçici tablo rollback ile temizlendi; gerçek veri değişmedi.",
        )
