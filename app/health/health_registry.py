# -*- coding: utf-8 -*-
"""Tüm sağlık kontrollerinin ve algoritma kataloğunun merkezi kaydı.

``all_checks`` runner tarafından kullanılır. ``ALGORITHM_CATALOG`` ise
Sistem Sağlığı sayfasındaki "Mevcut Kontroller / Algoritmalar" bölümünü
besler (ACTIVE / PLANNED / NOT_APPLICABLE).
"""

from __future__ import annotations

from app.health.checks.ahp_check import (
    AHPConsistencyRatioCheck,
    AHPMatrixShapeCheck,
    AHPReciprocalMatrixCheck,
    AHPWeightSumCheck,
    AlternativeCompletenessCheck,
    CriteriaCompletenessCheck,
    SensitivityReadinessCheck,
)
from app.health.checks.analytics_check import (
    AnalyticsDependencyCheck,
    ChartGenerationCheck,
    EmptyDatasetHandlingCheck,
    NumericDataAvailabilityCheck,
)
from app.health.checks.api_check import (
    ApiAppLoadCheck,
    ApiCorsSecurityCheck,
    ApiMiddlewareCheck,
    ApiRouterCheck,
)
from app.health.checks.architecture_check import (
    CircularImportCheck,
    DeadCodeHintCheck,
    DuplicateCodeHintCheck,
    LayerViolationCheck,
    ServiceLayerCheck,
)
from app.health.checks.backup_check import (
    BackupAgeCheck,
    BackupCreateCheck,
    BackupDirectoryCheck,
    BackupReadCheck,
)
from app.health.checks.base_check import BaseHealthCheck
from app.health.checks.benchmark_check import (
    BenchmarkDatasetCheck,
    BenchmarkExecutionCheck,
    RuntimeThresholdCheck,
)
from app.health.checks.config_check import (
    ConfigFilePresenceCheck,
    ConfigKeySanityCheck,
    EnvironmentConsistencyCheck,
)
from app.health.checks.data_quality_check import (
    DataProfilingCheck,
    DuplicateRecordCheck,
    MissingValueCheck,
    OrphanRecordCheck,
    OutlierDetectionCheck,
    RangeValidationCheck,
)
from app.health.checks.database_check import (
    SQLiteConnectionCheck,
    SQLiteForeignKeyCheck,
    SQLiteIntegrityCheck,
    SQLiteTableCountCheck,
    SQLiteWritePermissionCheck,
)
from app.health.checks.decision_check import (
    DecisionInputCheck,
    DecisionResultConsistencyCheck,
    RankingGenerationCheck,
    ScoreNormalizationCheck,
)
from app.health.checks.decision_center_check import (
    DecisionExplanationCheck,
    DecisionRunTraceabilityCheck,
    FairnessReportCheck,
    LowConfidenceGuardCheck,
    SensitivityResultCheck,
)
from app.health.checks.dependency_check import (
    ImportableCriticalPackagesCheck,
    MissingDependencyCheck,
    RequirementsPresenceCheck,
)
from app.health.checks.function_check import (
    BoundaryCheck,
    ContractCheck,
    ExceptionHandlingCheck,
    ImportCheck,
    ServiceFunctionCheck,
)
from app.health.checks.import_governance_check import (
    ImportDataConsistencyCheck,
    ImportInfrastructureCheck,
    ImportRollbackReadinessCheck,
)
from app.health.checks.log_check import (
    ErrorLogScannerCheck,
    LastErrorSnapshotCheck,
    LogDirectoryCheck,
    WarningCounterCheck,
)
from app.health.checks.ml_governance_check import (
    MLDecisionInfluenceCheck,
    MLDependencyCheck,
    MLExplainabilityCheck,
)
from app.health.checks.performance_check import (
    DatabaseConnectionTimeCheck,
    FunctionExecutionTimeCheck,
    MemoryUsageCheck,
    QueryPerformanceCheck,
    SlowQueryDetectionCheck,
)
from app.health.checks.period_planning_check import (
    CapacityConflictCheck,
    CoursePeriodMappingCheck,
    PeriodDataAvailabilityCheck,
    PlanningRuleCheck,
)
from app.health.checks.pool_lifecycle_check import (
    PoolStateMachineCheck,
    PoolStatusValidityCheck,
    PoolTransitionConsistencyCheck,
)
from app.health.checks.reporting_check import (
    ExcelExportCheck,
    ExportPermissionCheck,
    ImportFileValidationCheck,
    PDFExportCheck,
    ReportDirectoryCheck,
)
from app.health.checks.schema_check import (
    ColumnTypeCheck,
    ExpectedColumnsCheck,
    SchemaCompatibilityCheck,
    SchemaValidationCheck,
)
from app.health.checks.security_check import (
    DeveloperModeCheck,
    PathTraversalCheck,
    SensitiveLogCheck,
    SQLConsolePermissionCheck,
    UnsafeSQLPatternCheck,
)
from app.health.checks.startup_check import (
    AppEntrypointCheck,
    StartupConfigCheck,
    StartupDatabaseInitCheck,
)
from app.health.checks.system_info_check import SystemInfoCheck
from app.health.checks.table_view_check import (
    LargeTableSafetyCheck,
    TableListLoadCheck,
    TablePreviewCheck,
)
from app.health.checks.test_suite_check import (
    PytestAvailabilityCheck,
    TestDirectoryCheck,
    TestRunnerScriptCheck,
)
from app.health.checks.topsis_check import (
    TopsisDataAvailabilityCheck,
    TopsisNormalizationCheck,
    TopsisRankingValidityCheck,
)
from app.health.checks.ui_check import (
    EmptyStateCheck,
    PageLoadCheck,
    TabRegistrationCheck,
    WidgetExistenceCheck,
)

# Çalıştırılan tüm kontroller (sıra = rapor sırası).
_CHECK_CLASSES: list[type[BaseHealthCheck]] = [
    SystemInfoCheck,
    # Başlangıç
    AppEntrypointCheck,
    StartupConfigCheck,
    StartupDatabaseInitCheck,
    # Veritabanı
    SQLiteConnectionCheck,
    SQLiteIntegrityCheck,
    SQLiteForeignKeyCheck,
    SQLiteTableCountCheck,
    SQLiteWritePermissionCheck,
    # Şema
    SchemaValidationCheck,
    ExpectedColumnsCheck,
    SchemaCompatibilityCheck,
    ColumnTypeCheck,
    # Yapılandırma
    ConfigFilePresenceCheck,
    ConfigKeySanityCheck,
    EnvironmentConsistencyCheck,
    # Bağımlılık
    RequirementsPresenceCheck,
    MissingDependencyCheck,
    ImportableCriticalPackagesCheck,
    # Veri kalitesi
    MissingValueCheck,
    DuplicateRecordCheck,
    RangeValidationCheck,
    OrphanRecordCheck,
    DataProfilingCheck,
    OutlierDetectionCheck,
    # İçe aktarım yönetişimi
    ImportInfrastructureCheck,
    ImportRollbackReadinessCheck,
    ImportDataConsistencyCheck,
    # Fonksiyon
    ImportCheck,
    ServiceFunctionCheck,
    ContractCheck,
    ExceptionHandlingCheck,
    BoundaryCheck,
    # AHP
    AHPMatrixShapeCheck,
    AHPReciprocalMatrixCheck,
    AHPWeightSumCheck,
    AHPConsistencyRatioCheck,
    CriteriaCompletenessCheck,
    AlternativeCompletenessCheck,
    SensitivityReadinessCheck,
    # TOPSIS
    TopsisDataAvailabilityCheck,
    TopsisNormalizationCheck,
    TopsisRankingValidityCheck,
    # Karar
    DecisionInputCheck,
    RankingGenerationCheck,
    ScoreNormalizationCheck,
    DecisionResultConsistencyCheck,
    # Karar merkezi yönetişim
    DecisionRunTraceabilityCheck,
    DecisionExplanationCheck,
    FairnessReportCheck,
    SensitivityResultCheck,
    LowConfidenceGuardCheck,
    # Havuz yaşam döngüsü
    PoolStateMachineCheck,
    PoolStatusValidityCheck,
    PoolTransitionConsistencyCheck,
    # Dönem planlama
    PeriodDataAvailabilityCheck,
    CoursePeriodMappingCheck,
    CapacityConflictCheck,
    PlanningRuleCheck,
    # Raporlama
    ReportDirectoryCheck,
    ExportPermissionCheck,
    PDFExportCheck,
    ExcelExportCheck,
    ImportFileValidationCheck,
    # Analiz
    AnalyticsDependencyCheck,
    ChartGenerationCheck,
    NumericDataAvailabilityCheck,
    EmptyDatasetHandlingCheck,
    # Benchmark
    BenchmarkDatasetCheck,
    BenchmarkExecutionCheck,
    RuntimeThresholdCheck,
    # ML yönetişimi
    MLDecisionInfluenceCheck,
    MLExplainabilityCheck,
    MLDependencyCheck,
    # API
    ApiAppLoadCheck,
    ApiRouterCheck,
    ApiMiddlewareCheck,
    ApiCorsSecurityCheck,
    # Tablo görüntüleme
    TableListLoadCheck,
    TablePreviewCheck,
    LargeTableSafetyCheck,
    # Güvenlik
    SQLConsolePermissionCheck,
    UnsafeSQLPatternCheck,
    PathTraversalCheck,
    SensitiveLogCheck,
    DeveloperModeCheck,
    # Performans
    DatabaseConnectionTimeCheck,
    QueryPerformanceCheck,
    FunctionExecutionTimeCheck,
    MemoryUsageCheck,
    SlowQueryDetectionCheck,
    # Mimari
    LayerViolationCheck,
    CircularImportCheck,
    DuplicateCodeHintCheck,
    DeadCodeHintCheck,
    ServiceLayerCheck,
    # Log
    LogDirectoryCheck,
    ErrorLogScannerCheck,
    WarningCounterCheck,
    LastErrorSnapshotCheck,
    # Yedekleme
    BackupDirectoryCheck,
    BackupCreateCheck,
    BackupReadCheck,
    BackupAgeCheck,
    # Test paketi
    TestDirectoryCheck,
    TestRunnerScriptCheck,
    PytestAvailabilityCheck,
    # UI
    TabRegistrationCheck,
    PageLoadCheck,
    WidgetExistenceCheck,
    EmptyStateCheck,
]

# Audit modu: derin tarama odaklı kategoriler.
_AUDIT_CATEGORIES = {
    "Mimari",
    "Bağımlılık",
    "Güvenlik",
    "Log",
    "Test Paketi",
    "Yapılandırma",
}


def all_checks() -> list[BaseHealthCheck]:
    """Tam mod: kayıtlı tüm kontrollerin yeni örnekleri."""

    return [cls() for cls in _CHECK_CLASSES]


def quick_checks() -> list[BaseHealthCheck]:
    """Hızlı mod: uygulama açılışında çalışacak hafif kontroller."""

    return [cls() for cls in _CHECK_CLASSES if getattr(cls, "quick", False)]


def audit_checks() -> list[BaseHealthCheck]:
    """Audit modu: mimari, bağımlılık, güvenlik, log, test, config odaklı."""

    return [cls() for cls in _CHECK_CLASSES if cls.category in _AUDIT_CATEGORIES]


def check_count() -> int:
    return len(_CHECK_CLASSES)


# ---------------------------------------------------------------------------
# Algoritma / kontrol kataloğu (Sistem Sağlığı sayfasında listelenir).
# status: ACTIVE | PLANNED | NOT_APPLICABLE
# ---------------------------------------------------------------------------
ALGORITHM_CATALOG: list[dict[str, str]] = [
    {"name": "Health Check", "status": "ACTIVE", "purpose": "Tüm modüllerin sağlık kontrolünü çalıştırır.", "used_in": "Sistem Sağlığı", "state": "Çalışıyor"},
    {"name": "Heartbeat Check", "status": "ACTIVE", "purpose": "DB bağlantısının canlılığını ölçer.", "used_in": "Veritabanı Sağlığı", "state": "Çalışıyor"},
    {"name": "Smoke Test", "status": "ACTIVE", "purpose": "Kritik modüllerin import edilebilirliğini test eder.", "used_in": "Fonksiyon Kontrolleri", "state": "Çalışıyor"},
    {"name": "Sanity Check", "status": "ACTIVE", "purpose": "Temel değer/aralık makullüğünü doğrular.", "used_in": "Veri Kalitesi", "state": "Çalışıyor"},
    {"name": "Self-Test", "status": "ACTIVE", "purpose": "Servis sözleşmesini (ServiceResult) doğrular.", "used_in": "Fonksiyon Kontrolleri", "state": "Çalışıyor"},
    {"name": "Watchdog", "status": "PLANNED", "purpose": "Uzun süren işlemleri izler.", "used_in": "Performans", "state": "İleri aşama için planlandı"},
    {"name": "Dependency Check", "status": "ACTIVE", "purpose": "pandas/numpy/matplotlib bağımlılıklarını denetler.", "used_in": "Analiz & Grafik", "state": "Çalışıyor"},
    {"name": "Configuration Validation", "status": "ACTIVE", "purpose": "Geliştirici modu/SQL Console ayarlarını doğrular.", "used_in": "Güvenlik", "state": "Çalışıyor"},
    {"name": "SQLite Connection Test", "status": "ACTIVE", "purpose": "Veritabanı bağlantısının kurulup kurulmadığını kontrol eder.", "used_in": "Veritabanı Sağlığı", "state": "Çalışıyor"},
    {"name": "Schema Validation", "status": "ACTIVE", "purpose": "Beklenen tablo/kolon yapısını doğrular.", "used_in": "Şema", "state": "Çalışıyor"},
    {"name": "Migration Check", "status": "ACTIVE", "purpose": "Alembic migrasyon sürümünü kontrol eder.", "used_in": "Şema", "state": "Çalışıyor"},
    {"name": "SQLite PRAGMA integrity_check", "status": "ACTIVE", "purpose": "Veritabanı bütünlüğünü doğrular.", "used_in": "Veritabanı Sağlığı", "state": "Çalışıyor"},
    {"name": "SQLite PRAGMA foreign_key_check", "status": "ACTIVE", "purpose": "Yabancı anahtar tutarlılığını denetler.", "used_in": "Veritabanı Sağlığı", "state": "Çalışıyor"},
    {"name": "Duplicate Detection", "status": "ACTIVE", "purpose": "Tekrarlı kayıtları tespit eder.", "used_in": "Veri Kalitesi", "state": "Çalışıyor"},
    {"name": "Missing Value Check", "status": "ACTIVE", "purpose": "Zorunlu alanlardaki eksik değerleri bulur.", "used_in": "Veri Kalitesi", "state": "Çalışıyor"},
    {"name": "Referential Integrity Check", "status": "ACTIVE", "purpose": "Yetim/ilişkisiz kayıtları tespit eder.", "used_in": "Veri Kalitesi", "state": "Çalışıyor"},
    {"name": "Transaction Test", "status": "ACTIVE", "purpose": "Yazma iznini rollback ile güvenli test eder.", "used_in": "Veritabanı Sağlığı", "state": "Çalışıyor"},
    {"name": "Backup Validation", "status": "ACTIVE", "purpose": "Yedek alma/okuma/tazelik kontrolü.", "used_in": "Yedekleme", "state": "Çalışıyor"},
    {"name": "Completeness Check", "status": "ACTIVE", "purpose": "Kriter/alternatif eksiksizliğini doğrular.", "used_in": "AHP / Karar", "state": "Çalışıyor"},
    {"name": "Consistency Check", "status": "ACTIVE", "purpose": "Karar sonucu tutarlılığını denetler.", "used_in": "Karar Merkezi", "state": "Çalışıyor"},
    {"name": "Validity Check", "status": "ACTIVE", "purpose": "Değerlerin geçerli aralıkta olduğunu doğrular.", "used_in": "Veri Kalitesi", "state": "Çalışıyor"},
    {"name": "Range Check", "status": "ACTIVE", "purpose": "Negatif/mantıksız sayısal değer kontrolü.", "used_in": "Veri Kalitesi", "state": "Çalışıyor"},
    {"name": "Outlier Detection", "status": "ACTIVE", "purpose": "Aykırı değerleri istatistiksel tespit eder.", "used_in": "Veri Kalitesi", "state": "Çalışıyor"},
    {"name": "Z-Score", "status": "PLANNED", "purpose": "Standart skor ile aykırı değer tespiti.", "used_in": "Veri Kalitesi / İleri Analiz", "state": "IQR aktif; Z-Score planlandı"},
    {"name": "IQR Method", "status": "ACTIVE", "purpose": "Çeyrekler arası aralık ile aykırı tespiti.", "used_in": "Veri Kalitesi", "state": "Çalışıyor"},
    {"name": "Rule-Based Validation", "status": "ACTIVE", "purpose": "Tanımlı kurallarla veri doğrulama.", "used_in": "Veri Kalitesi", "state": "Çalışıyor"},
    {"name": "Data Profiling", "status": "ACTIVE", "purpose": "Tablo bazlı kayıt/kolon özetini çıkarır.", "used_in": "Veri Kalitesi", "state": "Çalışıyor"},
    {"name": "Unit Test", "status": "ACTIVE", "purpose": "Sözleşme/sınır birim testleri (gömülü).", "used_in": "Fonksiyon Kontrolleri", "state": "Çalışıyor"},
    {"name": "Integration Test", "status": "ACTIVE", "purpose": "Servis-DB entegrasyon doğrulaması.", "used_in": "Fonksiyon Kontrolleri", "state": "Çalışıyor"},
    {"name": "Regression Test", "status": "PLANNED", "purpose": "Önceki davranışların korunduğunu denetler.", "used_in": "Fonksiyon Kontrolleri", "state": "pytest paketinde mevcut; health entegrasyonu planlandı"},
    {"name": "Contract Test", "status": "ACTIVE", "purpose": "Fonksiyon çıktı sözleşmesini doğrular.", "used_in": "Fonksiyon Kontrolleri", "state": "Çalışıyor"},
    {"name": "Exception Test", "status": "ACTIVE", "purpose": "Hatalı girdide kontrollü hata doğrular.", "used_in": "Fonksiyon Kontrolleri", "state": "Çalışıyor"},
    {"name": "Boundary Test", "status": "ACTIVE", "purpose": "Boş/tek kayıt sınır durumlarını test eder.", "used_in": "Fonksiyon Kontrolleri", "state": "Çalışıyor"},
    {"name": "Mock Test", "status": "ACTIVE", "purpose": "Örnek/mock veri ile güvenli test.", "used_in": "Karar / Fonksiyon", "state": "Çalışıyor"},
    {"name": "End-to-End Test", "status": "PLANNED", "purpose": "Uçtan uca akış doğrulaması.", "used_in": "Fonksiyon Kontrolleri", "state": "e2e test paketinde; health entegrasyonu planlandı"},
    {"name": "Execution Time Measurement", "status": "ACTIVE", "purpose": "Kritik fonksiyon/sorgu süre ölçümü.", "used_in": "Performans", "state": "Çalışıyor"},
    {"name": "Slow Query Detection", "status": "ACTIVE", "purpose": "Yavaş sorguları tespit eder.", "used_in": "Performans", "state": "Çalışıyor"},
    {"name": "Memory Usage Check", "status": "PLANNED", "purpose": "Süreç bellek kullanımını ölçer.", "used_in": "Performans", "state": "psutil yoksa SKIPPED; opsiyonel"},
    {"name": "CPU Usage Check", "status": "PLANNED", "purpose": "CPU kullanımını ölçer.", "used_in": "Performans", "state": "psutil gerektirir; planlandı"},
    {"name": "Profiling", "status": "PLANNED", "purpose": "Ayrıntılı performans profili çıkarır.", "used_in": "Performans", "state": "İleri aşama için planlandı"},
    {"name": "Timeout Detection", "status": "PLANNED", "purpose": "Zaman aşımına uğrayan işlemleri tespit eder.", "used_in": "Performans", "state": "Planlandı"},
    {"name": "Load Test", "status": "NOT_APPLICABLE", "purpose": "Yük altında davranış testi.", "used_in": "Şimdilik gerekli değil", "state": "Masaüstü tek kullanıcı için zorunlu değil"},
    {"name": "Stress Test", "status": "NOT_APPLICABLE", "purpose": "Aşırı yük dayanıklılık testi.", "used_in": "Şimdilik gerekli değil", "state": "Masaüstü tek kullanıcı için zorunlu değil"},
    {"name": "AHP Pairwise Matrix Validation", "status": "ACTIVE", "purpose": "AHP karşılaştırma matrisini doğrular.", "used_in": "AHP", "state": "Çalışıyor"},
    {"name": "Reciprocal Matrix Check", "status": "ACTIVE", "purpose": "a[i][j]=1/a[j][i] kuralını denetler.", "used_in": "AHP", "state": "Çalışıyor"},
    {"name": "Consistency Ratio Check", "status": "ACTIVE", "purpose": "AHP tutarlılık oranını (CR) değerlendirir.", "used_in": "AHP", "state": "Çalışıyor"},
    {"name": "Eigenvector Calculation Check", "status": "ACTIVE", "purpose": "Özvektör tabanlı ağırlık/CR hesabı.", "used_in": "AHP", "state": "Çalışıyor"},
    {"name": "Weight Sum Check", "status": "ACTIVE", "purpose": "Ağırlık toplamının 1 olduğunu doğrular.", "used_in": "AHP", "state": "Çalışıyor"},
    {"name": "Criteria Completeness Check", "status": "ACTIVE", "purpose": "Kriterlerin eksiksizliğini denetler.", "used_in": "AHP / Karar", "state": "Çalışıyor"},
    {"name": "Alternative Completeness Check", "status": "ACTIVE", "purpose": "Alternatiflerin eksiksizliğini denetler.", "used_in": "AHP / Karar", "state": "Çalışıyor"},
    {"name": "Ranking Stability Check", "status": "PLANNED", "purpose": "Sıralamanın küçük değişimlere kararlılığı.", "used_in": "Karar / Duyarlılık", "state": "Duyarlılık altyapısı planlandı"},
    {"name": "Sensitivity Analysis", "status": "PLANNED", "purpose": "Ağırlık değişiminin sonuca etkisi.", "used_in": "Karar / Duyarlılık", "state": "Hazırlık kontrolü aktif; analiz planlandı"},
    {"name": "Normalization Check", "status": "ACTIVE", "purpose": "Skorların normalize edilebilirliğini denetler.", "used_in": "Karar Merkezi", "state": "Çalışıyor"},
    {"name": "Permission Check", "status": "ACTIVE", "purpose": "Rol/yetki kontrolü (SQL Console).", "used_in": "Güvenlik", "state": "Çalışıyor"},
    {"name": "SQL Injection Pattern Check", "status": "ACTIVE", "purpose": "Riskli SQL desenlerine karşı koruma denetimi.", "used_in": "Güvenlik", "state": "Çalışıyor"},
    {"name": "Input Sanitization", "status": "ACTIVE", "purpose": "Tanımlayıcı doğrulamasını test eder.", "used_in": "Güvenlik / Fonksiyon", "state": "Çalışıyor"},
    {"name": "Path Validation", "status": "ACTIVE", "purpose": "Path traversal korumasını denetler.", "used_in": "Güvenlik", "state": "Çalışıyor"},
    {"name": "Audit Log Check", "status": "ACTIVE", "purpose": "SQL Console denetim log altyapısını doğrular.", "used_in": "Güvenlik", "state": "Çalışıyor"},
    {"name": "Sensitive Data Check", "status": "ACTIVE", "purpose": "Loglarda hassas veri kalıbı arar.", "used_in": "Güvenlik", "state": "Çalışıyor"},
    {"name": "Role-Based Access Control", "status": "ACTIVE", "purpose": "Rol tabanlı erişim politikasını uygular.", "used_in": "Güvenlik", "state": "Çalışıyor"},
    {"name": "Error Log Scanner", "status": "ACTIVE", "purpose": "Loglarda ERROR/CRITICAL satırlarını tarar.", "used_in": "Log", "state": "Çalışıyor"},
    {"name": "Exception Frequency Analysis", "status": "PLANNED", "purpose": "Hata sıklığı analizini yapar.", "used_in": "Log", "state": "Planlandı"},
    {"name": "Warning Counter", "status": "ACTIVE", "purpose": "Log uyarı sayısını hesaplar.", "used_in": "Log", "state": "Çalışıyor"},
    {"name": "Critical Error Detection", "status": "ACTIVE", "purpose": "Kritik hataları tespit eder.", "used_in": "Log", "state": "Çalışıyor"},
    {"name": "Pattern Matching", "status": "ACTIVE", "purpose": "Regex tabanlı log/güvenlik kalıp eşleme.", "used_in": "Log / Güvenlik", "state": "Çalışıyor"},
    {"name": "Root Cause Grouping", "status": "PLANNED", "purpose": "Hataları kök nedene göre gruplar.", "used_in": "Log", "state": "Planlandı"},
    {"name": "Trend Analysis", "status": "PLANNED", "purpose": "Zaman içinde hata/uyarı eğilimi.", "used_in": "Log / Analiz", "state": "Planlandı"},
    {"name": "Last Error Snapshot", "status": "ACTIVE", "purpose": "Son hatayı kullanıcı dostu gösterir.", "used_in": "Log", "state": "Çalışıyor"},
    {"name": "Tab Load Check", "status": "ACTIVE", "purpose": "Sekme sınıflarının import edilebilirliği.", "used_in": "UI", "state": "Çalışıyor"},
    {"name": "Widget Existence Check", "status": "ACTIVE", "purpose": "Gerekli buton/çıktı alanı varlığı.", "used_in": "UI", "state": "Çalışıyor"},
    {"name": "Event Binding Check", "status": "PLANNED", "purpose": "UI olay bağlamalarını doğrular.", "used_in": "UI", "state": "Planlandı"},
    {"name": "Table Render Check", "status": "ACTIVE", "purpose": "Tablo önizleme/render güvenliği.", "used_in": "Tablo Görüntüleme", "state": "Çalışıyor"},
    {"name": "Empty State Check", "status": "ACTIVE", "purpose": "Boş veri durumu dayanıklılığı.", "used_in": "UI / Analiz", "state": "Çalışıyor"},
    {"name": "Navigation Check", "status": "PLANNED", "purpose": "Sekme/sayfa gezinme doğrulaması.", "used_in": "UI", "state": "Planlandı"},
    {"name": "UI Exception Check", "status": "ACTIVE", "purpose": "Sayfa import sırasında istisna denetimi.", "used_in": "UI", "state": "Çalışıyor"},
    {"name": "Layer Violation Detection", "status": "ACTIVE", "purpose": "UI'da doğrudan DB erişimini tespit eder.", "used_in": "Mimari", "state": "Çalışıyor"},
    {"name": "Import Dependency Scan", "status": "ACTIVE", "purpose": "Kritik modül import taraması.", "used_in": "Mimari / Fonksiyon", "state": "Çalışıyor"},
    {"name": "Circular Dependency Detection", "status": "ACTIVE", "purpose": "Döngüsel import tespiti.", "used_in": "Mimari", "state": "Çalışıyor"},
    {"name": "Service Layer Usage Check", "status": "ACTIVE", "purpose": "Servis/repository katmanı varlığı.", "used_in": "Mimari", "state": "Çalışıyor"},
    {"name": "Repository Pattern Check", "status": "ACTIVE", "purpose": "Repository deseni kullanımını doğrular.", "used_in": "Mimari", "state": "Çalışıyor"},
    {"name": "Dead Code Detection", "status": "ACTIVE", "purpose": "Olası ölü/geçici kod ipucu.", "used_in": "Mimari", "state": "İpucu seviyesinde çalışıyor"},
    {"name": "Duplicate Code Detection", "status": "ACTIVE", "purpose": "Yinelenen DB yardımcılarını işaretler.", "used_in": "Mimari", "state": "İpucu seviyesinde çalışıyor"},
    {"name": "Complexity Analysis", "status": "PLANNED", "purpose": "Kod karmaşıklığı ölçümü.", "used_in": "Mimari", "state": "Planlandı"},
    {"name": "Weighted Scoring", "status": "ACTIVE", "purpose": "Ağırlıklı genel sağlık puanı.", "used_in": "Sağlık Skoru", "state": "Çalışıyor"},
    {"name": "Rule-Based Scoring", "status": "ACTIVE", "purpose": "Durum bazlı kural ile skorlama.", "used_in": "Sağlık Skoru", "state": "Çalışıyor"},
    {"name": "Risk Matrix", "status": "PLANNED", "purpose": "Önem x olasılık risk matrisi.", "used_in": "Sağlık Skoru", "state": "Planlandı"},
    {"name": "FMEA", "status": "NOT_APPLICABLE", "purpose": "Hata türü ve etki analizi.", "used_in": "Şimdilik gerekli değil", "state": "Mevcut kapsam için zorunlu değil"},
    {"name": "Priority Ranking", "status": "ACTIVE", "purpose": "Önem seviyesine göre sıralama.", "used_in": "Sağlık Raporu", "state": "Çalışıyor"},
    {"name": "AHP-Based Health Score", "status": "PLANNED", "purpose": "AHP ile sağlık skoru ağırlıklandırma.", "used_in": "Sağlık Skoru", "state": "Sabit ağırlık aktif; AHP tabanlı planlandı"},
    {"name": "Threshold-Based Alerting", "status": "ACTIVE", "purpose": "Eşik tabanlı uyarı üretimi.", "used_in": "Performans / Sağlık", "state": "Çalışıyor"},
    {"name": "SLA/SLO Scoring", "status": "NOT_APPLICABLE", "purpose": "Servis seviyesi hedef skorlaması.", "used_in": "Şimdilik gerekli değil", "state": "Masaüstü uygulama için zorunlu değil"},
    {"name": "Anomaly Detection", "status": "PLANNED", "purpose": "Genel anomali tespiti.", "used_in": "Veri Kalitesi / İleri Analiz", "state": "Planlandı"},
    {"name": "Isolation Forest", "status": "PLANNED", "purpose": "Büyük veri setlerinde aykırı kayıt tespiti.", "used_in": "Veri Kalitesi / İleri Analiz", "state": "İleri aşama için planlandı"},
    {"name": "Local Outlier Factor", "status": "PLANNED", "purpose": "Yoğunluk tabanlı aykırı tespiti.", "used_in": "Veri Kalitesi / İleri Analiz", "state": "Planlandı"},
    {"name": "K-Means Clustering", "status": "PLANNED", "purpose": "Kümeleme tabanlı analiz.", "used_in": "İleri Analiz", "state": "Algoritma mevcut; health entegrasyonu planlandı"},
    {"name": "Decision Tree", "status": "PLANNED", "purpose": "Karar ağacı sınıflandırma.", "used_in": "İleri Analiz", "state": "Algoritma mevcut; health entegrasyonu planlandı"},
    {"name": "Random Forest", "status": "PLANNED", "purpose": "Topluluk sınıflandırma.", "used_in": "İleri Analiz", "state": "Algoritma mevcut; health entegrasyonu planlandı"},
    {"name": "Naive Bayes", "status": "PLANNED", "purpose": "Olasılıksal sınıflandırma.", "used_in": "İleri Analiz", "state": "Planlandı"},
    {"name": "Linear Regression", "status": "PLANNED", "purpose": "Sayısal tahmin.", "used_in": "İleri Analiz", "state": "Algoritma mevcut; health entegrasyonu planlandı"},
    {"name": "Time Series Analysis", "status": "NOT_APPLICABLE", "purpose": "Zaman serisi analizi.", "used_in": "Şimdilik gerekli değil", "state": "Mevcut veri yapısında zorunlu değil"},
    {"name": "ARIMA / Prophet", "status": "NOT_APPLICABLE", "purpose": "Zaman serisi tahmini yapar.", "used_in": "Şimdilik gerekli değil", "state": "Mevcut veri yapısında zorunlu değil"},
    {"name": "NLP Log Classification", "status": "NOT_APPLICABLE", "purpose": "Log sınıflandırma (NLP).", "used_in": "Şimdilik gerekli değil", "state": "Mevcut kapsam için zorunlu değil"},
    {"name": "Recommendation Algorithms", "status": "PLANNED", "purpose": "Öneri algoritmaları.", "used_in": "Karar / İleri Analiz", "state": "Karar motoru mevcut; ek öneri planlandı"},
]


# Yeni spesifikasyonun açıkça istediği, katalogda henüz tam adıyla
# bulunmayan kalemler. algorithm_catalog() bunları ada göre tekilleştirir.
_CATALOG_SUPPLEMENT: list[dict[str, str]] = [
    {"name": "AHP Consistency Ratio Check", "status": "ACTIVE", "purpose": "AHP tutarlılık oranını (CR) değerlendirir.", "used_in": "AHP", "state": "Çalışıyor"},
    {"name": "AHP Weight Sum Check", "status": "ACTIVE", "purpose": "AHP ağırlık toplamının 1 olduğunu doğrular.", "used_in": "AHP", "state": "Çalışıyor"},
    {"name": "TOPSIS Normalization Check", "status": "ACTIVE", "purpose": "TOPSIS normalize/ağırlıklı matris ve skor aralığını doğrular.", "used_in": "TOPSIS", "state": "Çalışıyor"},
    {"name": "Ranking Validation", "status": "ACTIVE", "purpose": "Sıralamanın tutarlı ve monoton olduğunu doğrular.", "used_in": "TOPSIS / Karar", "state": "Çalışıyor"},
    {"name": "Import Check", "status": "ACTIVE", "purpose": "Kritik modüllerin import edilebilirliğini test eder.", "used_in": "Fonksiyon / Bağımlılık", "state": "Çalışıyor"},
    {"name": "SQL Console Security Check", "status": "ACTIVE", "purpose": "SQL Console yetki ve ortam güvenliğini denetler.", "used_in": "Güvenlik", "state": "Çalışıyor"},
    {"name": "Configuration Validation", "status": "ACTIVE", "purpose": "config.json/ortam tutarlılığını doğrular.", "used_in": "Yapılandırma", "state": "Çalışıyor"},
    {"name": "Import Dependency Scan", "status": "ACTIVE", "purpose": "requirements vs. gerçek import farkını tarar.", "used_in": "Bağımlılık", "state": "Çalışıyor"},
    {"name": "Repository Pattern Check", "status": "ACTIVE", "purpose": "Repository deseni kullanımını doğrular.", "used_in": "Mimari", "state": "Çalışıyor"},
    {"name": "Memory Profiling", "status": "PLANNED", "purpose": "Ayrıntılı bellek profili çıkarır.", "used_in": "Performans", "state": "psutil gerektirir; planlandı"},
    {"name": "CPU Usage Check", "status": "PLANNED", "purpose": "CPU kullanımını ölçer.", "used_in": "Performans", "state": "psutil gerektirir; planlandı"},
    {"name": "Full Regression Test", "status": "PLANNED", "purpose": "Tüm regresyon paketini çalıştırır.", "used_in": "Test Paketi", "state": "pytest mevcut; health entegrasyonu planlandı"},
    {"name": "Predictive Failure Detection", "status": "PLANNED", "purpose": "Olası arızaları önceden tahmin eder.", "used_in": "İleri Analiz", "state": "Planlandı"},
]


def algorithm_catalog() -> list[dict[str, str]]:
    """Ana katalog + spesifikasyon eki (ada göre tekilleştirilmiş)."""

    merged: list[dict[str, str]] = list(ALGORITHM_CATALOG)
    seen = {item["name"].strip().lower() for item in merged}
    for item in _CATALOG_SUPPLEMENT:
        if item["name"].strip().lower() not in seen:
            merged.append(item)
            seen.add(item["name"].strip().lower())
    return merged
