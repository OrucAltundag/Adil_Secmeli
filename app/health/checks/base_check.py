# -*- coding: utf-8 -*-
"""Tüm sağlık kontrollerinin türediği temel sınıf ve çalışma bağlamı.

``safe_run`` her kontrolü izole çalıştırır: süreyi ölçer, exception'ı
yakalar, hatayı kullanıcı dostu + teknik detay olarak ayırır ve hiçbir
durumda uygulamayı çökertmez. Bir kontrolün hatası diğerlerini etkilemez.
"""

from __future__ import annotations

import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from app.core.config import AppConfig, load_app_config
from app.core.permissions import UserContext
from app.health.health_config import HealthConfig, default_health_config
from app.health.models import HealthCheckResult, HealthSeverity, HealthStatus
from app.repositories.sqlite_repository import SqliteRepository
from app.services.database_service import DatabaseService


@dataclass
class HealthContext:
    """Kontrollerin paylaştığı çalışma bağlamı."""

    app_config: AppConfig
    health_config: HealthConfig
    db_path: str | None
    user_context: UserContext | None
    mode: str = "full"  # "quick" | "full"
    developer_mode: bool = False
    database: DatabaseService | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        db_path: str | None = None,
        config: AppConfig | None = None,
        user_context: UserContext | None = None,
        mode: str = "full",
        health_config: HealthConfig | None = None,
    ) -> "HealthContext":
        cfg = config or load_app_config()
        hcfg = health_config or default_health_config()
        resolved_path = db_path or cfg.sqlite_db_path
        return cls(
            app_config=cfg,
            health_config=hcfg,
            db_path=resolved_path,
            user_context=user_context or UserContext.demo_admin(cfg),
            mode=mode,
            developer_mode=bool(cfg.enable_developer_tools or cfg.debug),
            database=DatabaseService(db_path=resolved_path, config=cfg),
        )

    @property
    def root(self) -> Path:
        return self.health_config.project_root

    def require_database(self) -> DatabaseService:
        """Optional `database` alanını çağrı bölgelerinde tipsel olarak daraltır."""
        if self.database is None:
            raise RuntimeError("HealthContext.database henüz başlatılmadı.")
        return self.database

    @contextmanager
    def repository(self) -> Iterator[SqliteRepository]:
        with self.require_database().repository() as repo:
            yield repo


class BaseHealthCheck:
    """Tüm kontroller için temel sınıf.

    Alt sınıflar ``name``, ``category`` ve ``run`` tanımlar. ``run``
    içinde serbestçe exception fırlatılabilir; ``safe_run`` bunu güvenle
    FAILED sonucuna çevirir.
    """

    name: str = "İsimsiz Kontrol"
    category: str = "Genel"
    #: Hızlı modda (uygulama açılışı) da çalışsın mı?
    quick: bool = False
    #: Skorlamada hangi kcategory bucket'ına gireceği (registry override edebilir).
    score_bucket: str = "architecture"
    default_severity: HealthSeverity = HealthSeverity.MEDIUM

    # -- Sonuç üreticileri --------------------------------------------------------
    def _result(
        self,
        status: HealthStatus,
        message: str,
        *,
        severity: HealthSeverity | None = None,
        detail: str = "",
        suggestion: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> HealthCheckResult:
        return HealthCheckResult(
            category=self.category,
            name=self.name,
            status=status.value,
            severity=(severity or self.default_severity).value,
            message=message,
            detail=detail,
            suggestion=suggestion,
            source=self.__class__.__name__,
            metadata=metadata or {},
        )

    def ok(self, message: str, **kw: Any) -> HealthCheckResult:
        kw.setdefault("severity", HealthSeverity.LOW)
        kw.setdefault("suggestion", "İşlem gerekmiyor.")
        return self._result(HealthStatus.OK, message, **kw)

    def info(self, message: str, **kw: Any) -> HealthCheckResult:
        kw.setdefault("severity", HealthSeverity.LOW)
        return self._result(HealthStatus.INFO, message, **kw)

    def warning(self, message: str, **kw: Any) -> HealthCheckResult:
        kw.setdefault("severity", HealthSeverity.MEDIUM)
        return self._result(HealthStatus.WARNING, message, **kw)

    def critical(self, message: str, **kw: Any) -> HealthCheckResult:
        kw.setdefault("severity", HealthSeverity.CRITICAL)
        return self._result(HealthStatus.CRITICAL, message, **kw)

    def skipped(self, message: str, **kw: Any) -> HealthCheckResult:
        kw.setdefault("severity", HealthSeverity.LOW)
        return self._result(HealthStatus.SKIPPED, message, **kw)

    def fixed(self, message: str, **kw: Any) -> HealthCheckResult:
        kw.setdefault("severity", HealthSeverity.LOW)
        kw.setdefault("suggestion", "Otomatik düzeltildi; ek işlem gerekmiyor.")
        result = self._result(HealthStatus.FIXED, message, **kw)
        result.auto_fix_available = True
        result.auto_fix_applied = True
        return result

    # -- Otomatik düzeltme (varsayılan: desteklenmez) ----------------------------
    def can_fix(self, context: HealthContext) -> bool:
        """Bu kontrol güvenli otomatik düzeltme sunuyor mu?"""

        return False

    def fix(self, context: HealthContext) -> HealthCheckResult | None:
        """Güvenli düzeltmeyi uygular ve FIXED sonucu döndürür."""

        return None

    # -- Çalıştırma ---------------------------------------------------------------
    def run(self, context: HealthContext) -> HealthCheckResult:
        raise NotImplementedError

    def safe_fix(self, context: HealthContext) -> HealthCheckResult | None:
        """fix()'i izole çalıştırır; hata olsa bile uygulamayı çökertmez."""

        start = time.perf_counter()
        try:
            if not self.can_fix(context):
                return None
            result = self.fix(context)
            if result is None:
                return None
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc(limit=4)
            result = HealthCheckResult(
                category=self.category,
                name=self.name,
                status=HealthStatus.FAILED.value,
                severity=HealthSeverity.MEDIUM.value,
                message=f"{self.name} otomatik düzeltmesi uygulanamadı.",
                detail=f"{type(exc).__name__}: {exc}\n{tb}",
                suggestion="Düzeltmeyi elle uygulayın; teknik detayı inceleyin.",
                source=self.__class__.__name__,
                auto_fix_available=True,
                auto_fix_applied=False,
            )
        result.category = self.category
        result.name = self.name
        if not result.source:
            result.source = self.__class__.__name__
        result.duration_ms = (time.perf_counter() - start) * 1000.0
        return result

    def safe_run(self, context: HealthContext) -> HealthCheckResult:
        """Kontrolü izole, süre ölçümlü ve çökertmeyen biçimde çalıştırır."""

        start = time.perf_counter()
        try:
            result = self.run(context)
            if result is None:  # savunmacı: run yanlışlıkla None döndürürse
                result = self.skipped(
                    "Kontrol sonuç üretmedi.",
                    detail="run() None döndürdü.",
                    suggestion="Kontrol uygulamasını gözden geçirin.",
                )
        except NotImplementedError:
            result = self.skipped(
                "Kontrol henüz uygulanmadı.",
                detail=f"{self.__class__.__name__}.run() tanımlı değil.",
                suggestion="Bu kontrol planlanan listededir.",
            )
        except Exception as exc:  # noqa: BLE001 - kontrol asla uygulamayı çökertmemeli
            tb = traceback.format_exc(limit=6)
            result = HealthCheckResult(
                category=self.category,
                name=self.name,
                status=HealthStatus.FAILED.value,
                severity=HealthSeverity.HIGH.value,
                message=f"{self.name} çalıştırılamadı.",
                detail=f"{type(exc).__name__}: {exc}\n{tb}",
                suggestion=(
                    "Hata teknik detayını geliştirici ile paylaşın; "
                    "kontrol izole çalıştığı için diğer kontroller etkilenmedi."
                ),
                source=self.__class__.__name__,
            )
        result.category = self.category
        result.name = self.name
        if not result.source:
            result.source = self.__class__.__name__
        result.duration_ms = (time.perf_counter() - start) * 1000.0
        return result
