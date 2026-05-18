# -*- coding: utf-8 -*-
"""AHP matris doğrulama, ağırlık ve tutarlılık hesaplama servisi."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

RI_BY_N = {
    1: 0.0,
    2: 0.0,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
}


@dataclass(slots=True)
class ValidationResult:
    is_valid: bool
    issues: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    normalized_data: Any = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ConsistencyResult:
    principal_eigenvalue: float | None
    consistency_index: float
    consistency_ratio: float
    is_consistent: bool
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AHPResult:
    criteria_keys: list[str]
    weights: dict[str, float]
    principal_eigenvalue: float | None
    consistency_index: float
    consistency_ratio: float
    is_consistent: bool
    warnings: list[str] = field(default_factory=list)
    calculation_method: str = "geometric_mean"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_pairwise_matrix(matrix: list[list[float]], criteria_keys: list[str] | None = None) -> ValidationResult:
    issues: list[dict[str, Any]] = []
    warnings: list[str] = []
    if not matrix or not isinstance(matrix, list):
        issues.append(_issue("empty_matrix", "AHP matrisi boş olamaz.", "Kriter sayısına uygun NxN matris girin."))
        return ValidationResult(False, issues, warnings)
    n = len(matrix)
    if criteria_keys is not None and len(criteria_keys) != n:
        issues.append(_issue("criteria_matrix_mismatch", "Kriter sayısı matris boyutuyla eşleşmiyor.", "Kriter listesi ve matris boyutunu eşitleyin."))
    normalized: list[list[float]] = []
    for i, row in enumerate(matrix):
        if not isinstance(row, list) or len(row) != n:
            issues.append(_issue("not_square", "AHP matrisi kare olmalıdır.", f"{i + 1}. satır {n} değer içermelidir."))
            continue
        normalized_row = []
        for j, raw in enumerate(row):
            try:
                value = float(raw)
            except (TypeError, ValueError):
                issues.append(_issue("invalid_numeric_value", f"{i + 1},{j + 1} hücresi sayısal olmalıdır.", "Saaty ölçeğinde 1/9 ile 9 arasında değer girin."))
                value = 1.0
            if value <= 0 or math.isnan(value) or math.isinf(value):
                issues.append(_issue("non_positive_value", f"{i + 1},{j + 1} hücresi pozitif olmalıdır.", "Negatif veya sıfır yerine Saaty ölçeği değeri girin."))
            if value < 1 / 9 - 1e-9 or value > 9 + 1e-9:
                warnings.append(f"{i + 1},{j + 1} hücresi Saaty 1/9-9 aralığı dışında görünüyor.")
            normalized_row.append(value)
        normalized.append(normalized_row)
    if len(normalized) == n and all(len(row) == n for row in normalized):
        for i in range(n):
            if not math.isclose(normalized[i][i], 1.0, rel_tol=1e-5, abs_tol=1e-5):
                issues.append(_issue("diagonal_not_one", f"{i + 1},{i + 1} diagonal değeri 1 olmalıdır.", "Diagonal değerleri kilitli 1 olarak ayarlayın."))
            for j in range(i + 1, n):
                expected = 1.0 / normalized[j][i] if normalized[j][i] else None
                if expected is None or not math.isclose(normalized[i][j], expected, rel_tol=1e-3, abs_tol=1e-3):
                    issues.append(_issue("reciprocal_mismatch", f"{i + 1},{j + 1} ve {j + 1},{i + 1} hücreleri reciprocal değil.", "Bir hücre değiştiğinde karşı hücreyi 1/değer olarak güncelleyin."))
    return ValidationResult(not issues, issues, warnings, normalized)


def calculate_weights_from_pairwise_matrix(criteria_keys: list[str], matrix: list[list[float]], method: str = "geometric_mean") -> AHPResult:
    validation = validate_pairwise_matrix(matrix, criteria_keys)
    if not validation.is_valid:
        messages = "; ".join(issue["message"] for issue in validation.issues)
        raise ValueError(f"AHP matrisi geçersiz: {messages}")
    n = len(criteria_keys)
    if n == 0:
        raise ValueError("En az bir kriter gereklidir.")
    if method == "eigenvector":
        weights, principal = _eigenvector_weights(matrix, criteria_keys)
        calculation_method = "eigenvector"
    else:
        weights = _geometric_mean_weights(matrix, criteria_keys)
        principal = _lambda_max(matrix, [weights[key] for key in criteria_keys])
        calculation_method = "geometric_mean"
    consistency = calculate_consistency(criteria_keys, matrix, weights)
    warnings = list(validation.warnings)
    warnings.extend(consistency.warnings)
    return AHPResult(
        criteria_keys=list(criteria_keys),
        weights=weights,
        principal_eigenvalue=principal,
        consistency_index=consistency.consistency_index,
        consistency_ratio=consistency.consistency_ratio,
        is_consistent=consistency.is_consistent,
        warnings=warnings,
        calculation_method=calculation_method,
    )


def calculate_consistency(criteria_keys: list[str], matrix: list[list[float]], weights: dict[str, float]) -> ConsistencyResult:
    n = len(criteria_keys)
    if n <= 2:
        return ConsistencyResult(float(n), 0.0, 0.0, True)
    normalized = normalize_weights(weights, criteria_keys)
    w = [normalized[key] for key in criteria_keys]
    lambda_max = _lambda_max(matrix, w)
    ci = (lambda_max - n) / (n - 1)
    ri = get_random_index(n)
    cr = 0.0 if ri == 0 else ci / ri
    warnings = []
    if cr > 0.10:
        warnings.append(f"Consistency Ratio {cr:.3f}; kabul edilebilir sınır 0.10 üzerindedir.")
    return ConsistencyResult(float(lambda_max), float(ci), float(cr), bool(cr <= 0.10), warnings)


def normalize_weights(weights: dict[str, float], criteria_keys: list[str] | None = None) -> dict[str, float]:
    keys = list(criteria_keys or weights.keys())
    safe = {}
    for key in keys:
        try:
            safe[key] = max(0.0, float(weights.get(key, 0.0)))
        except (TypeError, ValueError):
            safe[key] = 0.0
    total = sum(safe.values())
    if total <= 0:
        equal = 1.0 / max(1, len(keys))
        return {key: equal for key in keys}
    return {key: safe[key] / total for key in keys}


def build_pairwise_matrix_from_weights(weights: dict[str, float], criteria_keys: list[str] | None = None) -> list[list[float]]:
    keys = list(criteria_keys or weights.keys())
    normalized = normalize_weights(weights, keys)
    matrix = []
    for left in keys:
        row = []
        for right in keys:
            lv = normalized.get(left, 0.0) or 1e-9
            rv = normalized.get(right, 0.0) or 1e-9
            row.append(float(lv / rv))
        matrix.append(row)
    return matrix


def get_random_index(n: int) -> float:
    return float(RI_BY_N.get(int(n), 1.49))


def _geometric_mean_weights(matrix: list[list[float]], criteria_keys: list[str]) -> dict[str, float]:
    means = []
    for row in matrix:
        product = 1.0
        for value in row:
            product *= float(value)
        means.append(product ** (1.0 / len(criteria_keys)))
    total = sum(means) or 1.0
    return {key: means[idx] / total for idx, key in enumerate(criteria_keys)}


def _eigenvector_weights(matrix: list[list[float]], criteria_keys: list[str]) -> tuple[dict[str, float], float]:
    try:
        import numpy as np

        arr = np.array(matrix, dtype=float)
        eigenvalues, eigenvectors = np.linalg.eig(arr)
        idx = int(np.argmax(eigenvalues.real))
        vector = np.abs(np.real_if_close(eigenvectors[:, idx]).astype(float))
        total = float(vector.sum()) or 1.0
        weights = {key: float(vector[i] / total) for i, key in enumerate(criteria_keys)}
        return weights, float(eigenvalues[idx].real)
    except Exception:
        weights = _geometric_mean_weights(matrix, criteria_keys)
        return weights, _lambda_max(matrix, [weights[key] for key in criteria_keys])


def _lambda_max(matrix: list[list[float]], weights: list[float]) -> float:
    values = []
    for i, row in enumerate(matrix):
        weighted_sum = sum(float(row[j]) * float(weights[j]) for j in range(len(weights)))
        denom = float(weights[i]) if abs(float(weights[i])) > 1e-12 else 1e-12
        values.append(weighted_sum / denom)
    return sum(values) / len(values)


def _issue(code: str, message: str, suggestion: str) -> dict[str, str]:
    return {"code": code, "message": message, "suggestion": suggestion, "severity": "error"}
