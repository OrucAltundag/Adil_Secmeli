# -*- coding: utf-8 -*-
"""Yapılandırma (config) sağlık kontrolleri."""

from __future__ import annotations

import json

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _ConfigCheck(BaseHealthCheck):
    category = "Yapılandırma"
    score_bucket = "ops"


class ConfigFilePresenceCheck(_ConfigCheck):
    name = "Yapılandırma dosyası kontrolü"
    quick = True
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        root = context.root
        present = [f for f in context.health_config.config_files if (root / f).exists()]
        missing = [
            f for f in context.health_config.config_files if not (root / f).exists()
        ]
        if "requirements.txt" in missing:
            return self.warning(
                "requirements.txt bulunamadı.",
                detail=f"Mevcut: {present} • Eksik: {missing}",
                suggestion="Bağımlılık listesini requirements.txt olarak ekleyin.",
            )
        if missing:
            return self.info(
                "Bazı opsiyonel config dosyaları yok.",
                detail=f"Mevcut: {present} • Eksik: {missing}",
                suggestion="Gerekliyse eksik dosyaları oluşturun.",
            )
        return self.ok(
            "Beklenen yapılandırma dosyaları mevcut.",
            detail=", ".join(present),
        )


class ConfigKeySanityCheck(_ConfigCheck):
    name = "Yapılandırma anahtarı tutarlılık kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def can_fix(self, context: HealthContext) -> bool:
        path = context.root / "config.json"
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        return isinstance(data, dict) and "charts" not in data

    def fix(self, context: HealthContext) -> HealthCheckResult | None:
        path = context.root / "config.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or "charts" in data:
                return None
            data["charts"] = {"bins": 15}
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except (OSError, ValueError) as exc:
            return self.warning(
                "Eksik kozmetik config anahtarı eklenemedi.",
                detail=f"{path}: {exc}",
                suggestion="config.json yazma iznini kontrol edin.",
            )
        return self.fixed(
            "Eksik kozmetik config anahtarı eklendi.",
            detail=f"{path}: 'charts' varsayılanla eklendi.",
        )

    def run(self, context: HealthContext) -> HealthCheckResult:
        path = context.root / "config.json"
        if not path.exists():
            return self.info(
                "config.json yok; ortam değişkenleri/varsayılanlar kullanılıyor.",
                detail=str(path),
                suggestion="Gerekliyse config.json oluşturun.",
            )
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return self.critical(
                "config.json okunamadı / geçersiz JSON.",
                detail=f"{path}: {exc}",
                suggestion="config.json içeriğini düzeltin.",
            )
        if not isinstance(data, dict):
            return self.warning(
                "config.json beklenen nesne (dict) biçiminde değil.",
                detail=f"Tip: {type(data).__name__}",
                suggestion="config.json'u anahtar-değer nesnesi yapın.",
            )
        if "charts" not in data:
            return self.warning(
                "Kozmetik config anahtarı eksik ('charts').",
                detail="Grafik bin ayarı varsayılana düşecek.",
                suggestion="Otomatik düzeltme ile eklenebilir.",
            )
        return self.ok(
            "Yapılandırma anahtarları tutarlı.",
            detail=f"{len(data)} anahtar yüklendi.",
        )


class EnvironmentConsistencyCheck(_ConfigCheck):
    name = "Ortam tutarlılığı kontrolü"
    quick = True
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        cfg = context.app_config
        problems: list[str] = []
        if cfg.environment == "production" and cfg.debug:
            problems.append("DEBUG production ortamında açık.")
        if cfg.environment == "production" and cfg.enable_developer_tools:
            problems.append("Geliştirici araçları production'da açık.")
        if problems:
            return self.warning(
                "Ortam ayarları tutarsız.",
                detail="\n".join(problems),
                suggestion="Production'da debug/developer kapatın.",
            )
        return self.ok(
            "Ortam ayarları tutarlı.",
            detail=f"environment={cfg.environment}, debug={cfg.debug}",
        )
