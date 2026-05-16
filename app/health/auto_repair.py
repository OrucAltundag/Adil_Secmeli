# -*- coding: utf-8 -*-
"""Güvenli otomatik düzeltme sistemi.

Yalnızca GERİ DÖNÜŞÜ olmayan/riskli OLMAYAN işlemler yapılır:
eksik klasör/``__init__.py`` oluşturma, eksik kozmetik config anahtarı
ekleme ve kontrollerin kendi güvenli ``fix`` adımları.

ASLA yapılmaz: tablo/kolon/veri silme, migration zorlama, kullanıcı
verisi değiştirme, güvenlik ayarını sessizce düşürme, SQL Console'u
sessizce açma.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.health.checks.base_check import HealthContext
from app.health.health_config import HealthConfig, default_health_config
from app.health.models import HealthCheckResult, HealthSeverity, HealthStatus
from app.health.project_scanner import missing_dirs_for_repair

CATEGORY = "Otomatik Düzeltme"

# config.json'a eklenmesi güvenli (kozmetik) anahtarlar. Güvenlikle ilgili
# hiçbir anahtar burada YER ALMAZ.
SAFE_CONFIG_DEFAULTS: dict[str, object] = {
    "charts": {"bins": 15},
}


def _result(
    name: str,
    status: HealthStatus,
    message: str,
    detail: str = "",
    suggestion: str = "İşlem gerekmiyor.",
    severity: HealthSeverity = HealthSeverity.LOW,
    applied: bool = False,
) -> HealthCheckResult:
    return HealthCheckResult(
        category=CATEGORY,
        name=name,
        status=status.value,
        severity=severity.value,
        message=message,
        detail=detail,
        suggestion=suggestion,
        source="auto_repair",
        auto_fix_available=True,
        auto_fix_applied=applied,
    )


def _repair_directories(cfg: HealthConfig) -> list[HealthCheckResult]:
    results: list[HealthCheckResult] = []
    missing = missing_dirs_for_repair(cfg)
    if not missing:
        results.append(
            _result(
                "Klasör yapısı",
                HealthStatus.OK,
                "Beklenen tüm klasörler mevcut.",
                detail="logs, reports, data/backups, exports, health_reports",
            )
        )
        return results
    for path in missing:
        try:
            path.mkdir(parents=True, exist_ok=True)
            results.append(
                _result(
                    f"Eksik klasör oluşturuldu: {path.name}",
                    HealthStatus.FIXED,
                    f"'{path.name}' klasörü bulunamadı ve güvenli şekilde oluşturuldu.",
                    detail=str(path),
                    applied=True,
                )
            )
        except OSError as exc:
            results.append(
                _result(
                    f"Klasör oluşturulamadı: {path.name}",
                    HealthStatus.WARNING,
                    "Eksik klasör otomatik oluşturulamadı.",
                    detail=f"{path}: {exc}",
                    suggestion="Yazma izni olan bir konumda klasörü elle oluşturun.",
                    severity=HealthSeverity.MEDIUM,
                )
            )
    return results


def _repair_init_files(cfg: HealthConfig) -> list[HealthCheckResult]:
    results: list[HealthCheckResult] = []
    health_root = cfg.project_root / "app" / "health"
    targets = [health_root, health_root / "checks"]
    fixed_any = False
    for pkg in targets:
        if not pkg.is_dir():
            continue
        init_file = pkg / "__init__.py"
        if init_file.exists():
            continue
        try:
            init_file.write_text(
                "# -*- coding: utf-8 -*-\n", encoding="utf-8"
            )
            fixed_any = True
            results.append(
                _result(
                    f"Eksik __init__.py oluşturuldu: {pkg.name}",
                    HealthStatus.FIXED,
                    f"'{pkg.name}' paketinde __init__.py oluşturuldu.",
                    detail=str(init_file),
                    applied=True,
                )
            )
        except OSError as exc:
            results.append(
                _result(
                    f"__init__.py oluşturulamadı: {pkg.name}",
                    HealthStatus.WARNING,
                    "Eksik __init__.py otomatik oluşturulamadı.",
                    detail=f"{init_file}: {exc}",
                    suggestion="Dosyayı elle oluşturun.",
                    severity=HealthSeverity.MEDIUM,
                )
            )
    if not results and not fixed_any:
        results.append(
            _result(
                "Paket __init__.py kontrolü",
                HealthStatus.OK,
                "Health paketlerinde eksik __init__.py yok.",
            )
        )
    return results


def _repair_config_keys(cfg: HealthConfig) -> list[HealthCheckResult]:
    config_path = cfg.project_root / "config.json"
    if not config_path.exists():
        return [
            _result(
                "config.json anahtar kontrolü",
                HealthStatus.SKIPPED,
                "config.json bulunamadı; güvenlik gereği oluşturulmadı.",
                detail=str(config_path),
                suggestion="config.json'u elle oluşturup gözden geçirin.",
            )
        ]
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("config.json bir nesne (dict) değil")
    except (OSError, ValueError) as exc:
        return [
            _result(
                "config.json okunamadı",
                HealthStatus.WARNING,
                "config.json okunamadığı için anahtar onarımı atlandı.",
                detail=f"{config_path}: {exc}",
                suggestion="config.json içeriğini elle düzeltin.",
                severity=HealthSeverity.MEDIUM,
            )
        ]
    added = [k for k in SAFE_CONFIG_DEFAULTS if k not in data]
    if not added:
        return [
            _result(
                "config.json anahtar kontrolü",
                HealthStatus.OK,
                "Kozmetik config anahtarları tam.",
                detail=", ".join(SAFE_CONFIG_DEFAULTS.keys()),
            )
        ]
    for key in added:
        data[key] = SAFE_CONFIG_DEFAULTS[key]
    try:
        config_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as exc:
        return [
            _result(
                "config.json yazılamadı",
                HealthStatus.WARNING,
                "Eksik config anahtarı eklenemedi.",
                detail=f"{config_path}: {exc}",
                suggestion="config.json yazma iznini kontrol edin.",
                severity=HealthSeverity.MEDIUM,
            )
        ]
    return [
        _result(
            "Eksik config anahtarları eklendi",
            HealthStatus.FIXED,
            f"Varsayılanla eklenen anahtarlar: {', '.join(added)}",
            detail=str(config_path),
            applied=True,
        )
    ]


class AutoRepair:
    """Güvenli düzeltmeleri çalıştırır; sonuçları HealthCheckResult döndürür."""

    def __init__(self, config: HealthConfig | None = None):
        self.config = config or default_health_config()

    def run(self, context: HealthContext | None = None) -> list[HealthCheckResult]:
        results: list[HealthCheckResult] = []
        results.extend(_repair_directories(self.config))
        results.extend(_repair_init_files(self.config))
        results.extend(_repair_config_keys(self.config))

        # Kontrollerin kendi güvenli düzeltmeleri (varsa).
        if context is not None:
            try:
                from app.health.health_registry import all_checks

                for check in all_checks():
                    try:
                        if check.can_fix(context):
                            fixed = check.safe_fix(context)
                            if fixed is not None:
                                results.append(fixed)
                    except Exception:  # noqa: BLE001 - tek fix diğerini etkilemez
                        continue
            except Exception:  # noqa: BLE001
                pass
        return results


def run_auto_repair(
    context: HealthContext | None = None, config: HealthConfig | None = None
) -> list[HealthCheckResult]:
    return AutoRepair(config=config).run(context=context)
