# -*- coding: utf-8 -*-
"""AHP (Analitik Hiyerarşi Süreci) sağlık kontrolleri."""

from __future__ import annotations

import json

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


def _load_active_ahp_profile(context: HealthContext) -> dict | None:
    """Aktif AHP ağırlık profilini güvenli şekilde okur."""

    with context.repository() as repo:
        if not repo.table_exists("ahp_weight_profiles"):
            return None
        cols = set(repo.column_names("ahp_weight_profiles"))
        order = "is_active DESC, id DESC" if "is_active" in cols else "id DESC"
        row = repo.fetchone(
            "SELECT weights_json, pairwise_matrix_json, criteria_keys_json, "
            "consistency_ratio FROM ahp_weight_profiles "
            f"ORDER BY {order} LIMIT 1"
        )
    if not row:
        return None

    def _parse(value):
        try:
            return json.loads(value) if value else None
        except (TypeError, ValueError):
            return None

    return {
        "weights": _parse(row[0]),
        "matrix": _parse(row[1]),
        "criteria": _parse(row[2]),
        "consistency_ratio": row[3],
    }


class _AHPCheck(BaseHealthCheck):
    category = "AHP"
    score_bucket = "ahp_decision"

    def _no_profile(self) -> HealthCheckResult:
        return self.info(
            "AHP ağırlık profili bulunamadı.",
            detail="ahp_weight_profiles tablosu boş veya tablo yok.",
            suggestion="AHP Ağırlık Yönetimi sekmesinden bir profil oluşturun.",
        )


class AHPMatrixShapeCheck(_AHPCheck):
    name = "AHP matris şekli kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        profile = _load_active_ahp_profile(context)
        if not profile:
            return self._no_profile()
        matrix = profile.get("matrix")
        if not matrix:
            return self.info(
                "AHP karşılaştırma matrisi kayıtlı değil.",
                detail="pairwise_matrix_json boş.",
                suggestion="Ağırlıklar matris olmadan da kullanılabilir; bilgilendirme.",
            )
        n = len(matrix)
        square = all(isinstance(r, (list, tuple)) and len(r) == n for r in matrix)
        if not square:
            return self.critical(
                "AHP matrisi kare değil.",
                detail=f"Satır sayısı {n}, satır uzunlukları tutarsız.",
                suggestion="AHP karşılaştırma matrisini kare biçimde yeniden oluşturun.",
            )
        return self.ok(
            f"AHP matrisi kare ({n}x{n}).",
            detail="Matris boyutları tutarlı.",
            metadata={"n": n},
        )


class AHPReciprocalMatrixCheck(_AHPCheck):
    name = "AHP karşılıklılık (reciprocal) kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        profile = _load_active_ahp_profile(context)
        if not profile:
            return self._no_profile()
        matrix = profile.get("matrix")
        if not matrix:
            return self.info(
                "AHP matrisi kayıtlı değil.",
                detail="pairwise_matrix_json boş.",
                suggestion="Bilgilendirme amaçlıdır.",
            )
        n = len(matrix)
        bad: list[str] = []
        for i in range(n):
            for j in range(n):
                try:
                    a = float(matrix[i][j])
                    b = float(matrix[j][i])
                except (TypeError, ValueError, IndexError):
                    bad.append(f"[{i}][{j}] sayısal değil")
                    continue
                if i == j:
                    if abs(a - 1.0) > 1e-6:
                        bad.append(f"köşegen [{i}][{i}]={a} (1 olmalı)")
                elif b == 0 or abs(a - 1.0 / b) > 1e-3:
                    bad.append(f"[{i}][{j}]={a} ≠ 1/[{j}][{i}]")
        if bad:
            return self.warning(
                "AHP matrisi karşılıklılık kuralını tam sağlamıyor.",
                detail="\n".join(bad[:15]),
                suggestion="a[i][j] = 1 / a[j][i] olacak şekilde matrisi düzeltin.",
                metadata={"violations": len(bad)},
            )
        return self.ok(
            "AHP matrisi karşılıklılık kuralına uyuyor.",
            detail="a[i][j] = 1 / a[j][i] sağlanıyor.",
        )


class AHPWeightSumCheck(_AHPCheck):
    name = "AHP ağırlık toplamı kontrolü"
    default_severity = HealthSeverity.HIGH

    def run(self, context: HealthContext) -> HealthCheckResult:
        profile = _load_active_ahp_profile(context)
        if not profile:
            return self._no_profile()
        weights = profile.get("weights")
        values: list[float] = []
        if isinstance(weights, dict):
            values = [float(v) for v in weights.values()]
        elif isinstance(weights, (list, tuple)):
            values = [float(v) for v in weights]
        if not values:
            return self.info(
                "AHP ağırlıkları okunamadı.",
                detail=f"weights_json tipi: {type(weights).__name__}",
                suggestion="Profil ağırlıklarını yeniden hesaplayın.",
            )
        total = sum(values)
        tol = context.health_config.ahp_weight_sum_tolerance
        if abs(total - 1.0) <= tol:
            return self.ok(
                "AHP ağırlık toplamı 1'e yakın.",
                detail=f"Toplam = {total:.6f} (tolerans {tol})",
                metadata={"sum": total},
            )
        return self.critical(
            "AHP ağırlık toplamı 1 olmalıdır.",
            detail=f"Toplam = {total:.6f}, sapma = {abs(total - 1.0):.6f}",
            suggestion="AHP ağırlıklarını normalize edip yeniden hesaplayın.",
            metadata={"sum": total},
        )


class AHPConsistencyRatioCheck(_AHPCheck):
    name = "AHP tutarlılık oranı (CR) kontrolü"
    default_severity = HealthSeverity.HIGH

    def run(self, context: HealthContext) -> HealthCheckResult:
        profile = _load_active_ahp_profile(context)
        if not profile:
            return self._no_profile()
        cr = profile.get("consistency_ratio")
        matrix = profile.get("matrix")
        if cr is None and matrix:
            cr = self._compute_cr(matrix)
        if cr is None:
            return self.info(
                "Tutarlılık oranı hesaplanamadı.",
                detail="consistency_ratio kayıtlı değil ve matris yok.",
                suggestion="AHP matrisini kaydedip CR'yi yeniden hesaplayın.",
            )
        cr = float(cr)
        ok_t = context.health_config.ahp_cr_ok
        warn_t = context.health_config.ahp_cr_warning
        meta = {"consistency_ratio": cr}
        if cr <= ok_t:
            return self.ok(
                f"AHP tutarlılık oranı kabul edilebilir (CR={cr:.4f}).",
                detail=f"CR ≤ {ok_t}",
                metadata=meta,
            )
        if cr <= warn_t:
            return self.warning(
                f"AHP tutarlılık oranı sınırda (CR={cr:.4f}).",
                detail=f"{ok_t} < CR ≤ {warn_t}",
                suggestion="Karşılaştırmaları gözden geçirip tutarlılığı artırın.",
                metadata=meta,
            )
        return self.critical(
            f"AHP tutarlılık oranı çok yüksek (CR={cr:.4f}).",
            detail=f"CR > {warn_t}",
            suggestion="AHP ikili karşılaştırmalarını yeniden yapın.",
            metadata=meta,
        )

    @staticmethod
    def _compute_cr(matrix) -> float | None:
        try:
            import numpy as np

            from app.algorithms.mcdm.ahp import RI_TABLE

            arr = np.array(matrix, dtype=float)
            n = arr.shape[0]
            if n < 2 or arr.shape[0] != arr.shape[1]:
                return 0.0
            eigvals = np.linalg.eigvals(arr)
            lambda_max = float(np.max(eigvals.real))
            ci = (lambda_max - n) / (n - 1)
            ri = RI_TABLE.get(n, RI_TABLE[10])
            return float(ci / ri) if ri else 0.0
        except Exception:  # noqa: BLE001
            return None


class CriteriaCompletenessCheck(_AHPCheck):
    name = "Kriter eksiksizlik kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            if not repo.table_exists("decision_criteria_definitions"):
                return self.info(
                    "Kriter tanımı tablosu bulunamadı.",
                    detail="decision_criteria_definitions tablosu yok.",
                    suggestion="Kriter tanımlarını oluşturun.",
                )
            count = repo.row_count("decision_criteria_definitions")
        if count == 0:
            return self.warning(
                "Tanımlı karar kriteri yok.",
                detail="decision_criteria_definitions boş.",
                suggestion="Karar için en az birkaç kriter tanımlayın.",
            )
        return self.ok(
            f"Karar kriterleri tanımlı ({count}).",
            detail=f"decision_criteria_definitions: {count} kayıt",
            metadata={"criteria_count": count},
        )


class AlternativeCompletenessCheck(_AHPCheck):
    name = "Alternatif eksiksizlik kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            if not repo.table_exists("havuz"):
                return self.info(
                    "Havuz tablosu bulunamadı.",
                    detail="havuz tablosu yok.",
                    suggestion="Havuz verisini oluşturun.",
                )
            count = repo.row_count("havuz")
        if count == 0:
            return self.warning(
                "Karar için alternatif (havuz dersi) yok.",
                detail="havuz tablosu boş.",
                suggestion="Havuz tablosunu müfredat yıllarından doldurun.",
            )
        return self.ok(
            f"Karar alternatifleri mevcut ({count}).",
            detail=f"havuz: {count} kayıt",
            metadata={"alternative_count": count},
        )


class SensitivityReadinessCheck(_AHPCheck):
    name = "Duyarlılık analizi hazırlık kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            has_profile = repo.table_exists("ahp_weight_profiles") and (
                repo.row_count("ahp_weight_profiles") > 0
            )
            has_items = repo.table_exists("ahp_course_sensitivity_items")
        if has_profile and has_items:
            return self.ok(
                "Duyarlılık analizi için gerekli yapı mevcut.",
                detail="AHP profili ve duyarlılık tabloları hazır.",
            )
        return self.info(
            "Duyarlılık analizi için veri eksik olabilir.",
            detail=f"profil={has_profile}, sensitivity_items_tablosu={has_items}",
            suggestion="AHP profili oluşturup duyarlılık analizini çalıştırın.",
        )
