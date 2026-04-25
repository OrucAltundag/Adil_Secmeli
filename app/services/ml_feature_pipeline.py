# -*- coding: utf-8 -*-
"""ML için ortak feature üretim ve kalite pipeline'ı."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime
import json
import sqlite3
from typing import Any

import pandas as pd

from app.db.schema_compat import ensure_ml_governance_schema


FEATURE_SCHEMA_VERSION = "course_features_v1"


@dataclass
class MLFeatureDataset:
    X: pd.DataFrame
    y: pd.Series | None
    feature_names: list[str]
    feature_schema_version: str
    sample_count: int
    missing_features_summary: dict[str, Any] = field(default_factory=dict)
    imputation_strategy: dict[str, Any] = field(default_factory=dict)
    normalization_summary: dict[str, Any] = field(default_factory=dict)
    raw_data_summary: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        data = asdict(self)
        data["X"] = self.X.to_dict(orient="records")
        data["y"] = self.y.tolist() if self.y is not None else None
        return data


FEATURE_COLUMNS = [
    "success_rate",
    "average_grade_normalized",
    "enrollment_rate",
    "capacity",
    "enrolled_students",
    "survey_count",
    "survey_rate",
    "popularity_score",
    "trend_score",
    "previous_topsis_score",
    "years_in_pool",
    "years_in_rest",
    "course_age",
    "faculty_id_encoded",
    "department_id_encoded",
    "course_type_encoded",
]


def get_feature_schema_version() -> str:
    return FEATURE_SCHEMA_VERSION


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table_name,))
    return bool(cur.fetchone())


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
        if pd.isna(out):
            return default
        return out
    except Exception:
        return default


def build_course_feature_dataset(
    conn: sqlite3.Connection,
    *,
    scope: dict | None = None,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    save_snapshot: bool = False,
) -> MLFeatureDataset:
    """Ders-yıl seviyesinde ML feature veri seti üretir."""
    raw_df = _load_raw_course_rows(conn, year=year, faculty_id=faculty_id, department_id=department_id)
    warnings: list[str] = []
    if raw_df.empty:
        warnings.append("ML feature üretimi için ders/kriter verisi bulunamadı.")
        dataset = MLFeatureDataset(
            X=pd.DataFrame(columns=FEATURE_COLUMNS),
            y=None,
            feature_names=FEATURE_COLUMNS,
            feature_schema_version=FEATURE_SCHEMA_VERSION,
            sample_count=0,
            raw_data_summary={"row_count": 0},
            warnings=warnings,
        )
        if save_snapshot:
            save_feature_snapshot(conn, dataset, scope=scope, year=year, faculty_id=faculty_id, department_id=department_id)
        return dataset

    normalized, norm_summary = normalize_features(raw_df)
    feature_df, imputation = impute_missing_values(normalized[FEATURE_COLUMNS], strategy="median")
    schema_issues = validate_feature_schema(feature_df)
    warnings.extend(schema_issues)
    missing_summary = _missing_summary(normalized[FEATURE_COLUMNS])

    target = None
    if "target_status" in normalized.columns:
        target = normalized["target_status"].astype(int)

    dataset = MLFeatureDataset(
        X=feature_df[FEATURE_COLUMNS],
        y=target,
        feature_names=FEATURE_COLUMNS,
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        sample_count=int(len(feature_df)),
        missing_features_summary=missing_summary,
        imputation_strategy=imputation,
        normalization_summary=norm_summary,
        raw_data_summary={
            "row_count": int(len(raw_df)),
            "year_filter": year,
            "faculty_id": faculty_id,
            "department_id": department_id,
        },
        warnings=warnings,
    )
    if save_snapshot:
        save_feature_snapshot(conn, dataset, scope=scope, year=year, faculty_id=faculty_id, department_id=department_id)
    return dataset


def _load_raw_course_rows(
    conn: sqlite3.Connection,
    *,
    year: int | None,
    faculty_id: int | None,
    department_id: int | None,
) -> pd.DataFrame:
    if not _table_exists(conn, "ders"):
        return pd.DataFrame()

    has_kriteria = _table_exists(conn, "ders_kriterleri")
    has_perf = _table_exists(conn, "performans")
    has_pop = _table_exists(conn, "populerlik")
    has_skor = _table_exists(conn, "skor")
    has_havuz = _table_exists(conn, "havuz")

    select_parts = [
        "d.ders_id",
        "COALESCE(d.fakulte_id, h.fakulte_id) AS faculty_id",
        "d.bolum_id AS department_id",
        "COALESCE(d.DersTipi, d.tip, '') AS course_type",
        "COALESCE(dk.yil, p.akademik_yil, pop.akademik_yil, s.akademik_yil, h.yil) AS feature_year",
    ]
    joins = []
    if has_havuz:
        joins.append("LEFT JOIN havuz h ON CAST(h.ders_id AS INTEGER) = d.ders_id")
        select_parts.extend(["h.statu AS target_status", "h.sayac AS years_in_pool_hint"])
    else:
        joins.append("LEFT JOIN (SELECT NULL AS fakulte_id, NULL AS yil, NULL AS ders_id, NULL AS statu, NULL AS sayac) h ON 1=0")
        select_parts.extend(["NULL AS target_status", "0 AS years_in_pool_hint"])
    if has_kriteria:
        joins.append("LEFT JOIN ders_kriterleri dk ON dk.ders_id = d.ders_id")
        select_parts.extend([
            "dk.toplam_ogrenci",
            "dk.gecen_ogrenci",
            "dk.basari_ortalamasi",
            "dk.kontenjan AS dk_kontenjan",
            "dk.kayitli_ogrenci",
            "dk.anket_katilimci",
            "dk.anket_dersi_secen",
        ])
    else:
        joins.append("LEFT JOIN (SELECT NULL AS ders_id, NULL AS yil) dk ON 1=0")
        select_parts.extend(["NULL AS toplam_ogrenci", "NULL AS gecen_ogrenci", "NULL AS basari_ortalamasi", "NULL AS dk_kontenjan", "NULL AS kayitli_ogrenci", "NULL AS anket_katilimci", "NULL AS anket_dersi_secen"])
    if has_perf:
        joins.append("LEFT JOIN performans p ON p.ders_id = d.ders_id AND (dk.yil IS NULL OR p.akademik_yil = dk.yil)")
        select_parts.extend(["p.basari_orani", "p.ortalama_not"])
    else:
        joins.append("LEFT JOIN (SELECT NULL AS ders_id, NULL AS akademik_yil) p ON 1=0")
        select_parts.extend(["NULL AS basari_orani", "NULL AS ortalama_not"])
    if has_pop:
        joins.append("LEFT JOIN populerlik pop ON pop.ders_id = d.ders_id AND (dk.yil IS NULL OR pop.akademik_yil = dk.yil)")
        select_parts.extend(["pop.talep_sayisi", "pop.kontenjan AS pop_kontenjan", "pop.doluluk_orani", "pop.ham_puan AS popularity_score_raw"])
    else:
        joins.append("LEFT JOIN (SELECT NULL AS ders_id, NULL AS akademik_yil) pop ON 1=0")
        select_parts.extend(["NULL AS talep_sayisi", "NULL AS pop_kontenjan", "NULL AS doluluk_orani", "NULL AS popularity_score_raw"])
    if has_skor:
        joins.append("LEFT JOIN skor s ON s.ders_id = d.ders_id AND (dk.yil IS NULL OR s.akademik_yil = dk.yil)")
        select_parts.append("s.skor_top AS previous_topsis_score")
    else:
        joins.append("LEFT JOIN (SELECT NULL AS ders_id, NULL AS akademik_yil) s ON 1=0")
        select_parts.append("NULL AS previous_topsis_score")

    where = ["COALESCE(dk.yil, p.akademik_yil, pop.akademik_yil, s.akademik_yil, h.yil) IS NOT NULL"]
    params: list[Any] = []
    if year is not None:
        where.append("COALESCE(dk.yil, p.akademik_yil, pop.akademik_yil, s.akademik_yil, h.yil) = ?")
        params.append(int(year))
    if faculty_id is not None:
        where.append("COALESCE(d.fakulte_id, h.fakulte_id) = ?")
        params.append(int(faculty_id))
    if department_id is not None:
        where.append("d.bolum_id = ?")
        params.append(int(department_id))

    sql = f"""
        SELECT {", ".join(select_parts)}
        FROM ders d
        {" ".join(joins)}
        WHERE {" AND ".join(where)}
        GROUP BY d.ders_id, feature_year
        ORDER BY feature_year, d.ders_id
    """
    try:
        return pd.read_sql_query(sql, conn, params=params)
    except Exception:
        return pd.DataFrame()


def normalize_features(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    df = raw_df.copy()
    summary: dict[str, Any] = {"rules": []}
    total_students = df.get("toplam_ogrenci", pd.Series([0] * len(df))).map(_safe_float)
    passed_students = df.get("gecen_ogrenci", pd.Series([0] * len(df))).map(_safe_float)
    success_rate = df.get("basari_orani", pd.Series([None] * len(df))).map(lambda v: _safe_float(v, -1.0))
    df["success_rate"] = [
        min(max(sr if sr >= 0 else (p / t if t > 0 else 0.0), 0.0), 1.0)
        for sr, p, t in zip(success_rate, passed_students, total_students)
    ]
    summary["rules"].append("success_rate 0-1 aralığına normalize edildi.")

    avg = df.get("basari_ortalamasi", df.get("ortalama_not", pd.Series([0] * len(df)))).map(_safe_float)
    avg_max = float(avg.max()) if len(avg) else 100.0
    scale = 4.0 if avg_max <= 4.5 else 100.0
    df["average_grade_normalized"] = avg.map(lambda v: min(max(v / scale, 0.0), 1.0))
    summary["average_grade_scale"] = scale

    capacity = df.get("dk_kontenjan", df.get("pop_kontenjan", pd.Series([0] * len(df)))).map(_safe_float)
    enrolled = df.get("kayitli_ogrenci", df.get("talep_sayisi", pd.Series([0] * len(df)))).map(_safe_float)
    df["capacity"] = capacity
    df["enrolled_students"] = enrolled
    df["enrollment_rate"] = [min(max(e / c, 0.0), 1.5) if c > 0 else 0.0 for e, c in zip(enrolled, capacity)]
    summary["rules"].append("capacity=0 olduğunda enrollment_rate 0 kabul edildi.")

    survey_count = df.get("anket_katilimci", pd.Series([0] * len(df))).map(_safe_float)
    survey_selected = df.get("anket_dersi_secen", pd.Series([0] * len(df))).map(_safe_float)
    df["survey_count"] = survey_count
    df["survey_rate"] = [min(max(s / c, 0.0), 1.0) if c > 0 else 0.0 for s, c in zip(survey_selected, survey_count)]
    df["popularity_score"] = df.get("popularity_score_raw", df.get("doluluk_orani", pd.Series([0] * len(df)))).map(_safe_float)

    df = df.sort_values(["ders_id", "feature_year"])
    df["trend_score"] = (
        df.groupby("ders_id")["success_rate"]
        .transform(lambda s: s.rolling(3, min_periods=1).mean())
        .fillna(df["success_rate"])
    )
    df["previous_topsis_score"] = df.get("previous_topsis_score", pd.Series([0] * len(df))).map(_safe_float)
    df["years_in_pool"] = df.get("years_in_pool_hint", pd.Series([0] * len(df))).map(lambda v: max(int(_safe_float(v)), 0))
    df["years_in_rest"] = df.get("target_status", pd.Series([0] * len(df))).map(lambda v: 1 if int(_safe_float(v, 0)) == -1 else 0)
    first_year = df.groupby("ders_id")["feature_year"].transform("min")
    df["course_age"] = (df["feature_year"] - first_year).fillna(0).clip(lower=0)
    df["faculty_id_encoded"] = df.get("faculty_id", pd.Series([0] * len(df))).map(lambda v: int(_safe_float(v)))
    df["department_id_encoded"] = df.get("department_id", pd.Series([0] * len(df))).map(lambda v: int(_safe_float(v)))
    type_codes = {name: idx + 1 for idx, name in enumerate(sorted(set(str(v or "") for v in df.get("course_type", []))))}
    df["course_type_encoded"] = df.get("course_type", pd.Series([""] * len(df))).map(lambda v: type_codes.get(str(v or ""), 0))
    return df, summary


def impute_missing_values(df: pd.DataFrame, strategy: str = "median") -> tuple[pd.DataFrame, dict[str, Any]]:
    out = df.copy()
    report = {"strategy": strategy, "columns": {}}
    for col in out.columns:
        missing = int(out[col].isna().sum())
        if missing == 0:
            continue
        if strategy == "mean":
            fill_value = float(out[col].mean()) if not out[col].dropna().empty else 0.0
        elif strategy == "zero":
            fill_value = 0.0
        else:
            fill_value = float(out[col].median()) if not out[col].dropna().empty else 0.0
        out[col] = out[col].fillna(fill_value)
        report["columns"][col] = {"missing_count": missing, "fill_value": fill_value}
    return out.fillna(0.0), report


def validate_feature_schema(df: pd.DataFrame) -> list[str]:
    warnings = []
    missing = [col for col in FEATURE_COLUMNS if col not in df.columns]
    if missing:
        warnings.append(f"Eksik feature kolonları: {', '.join(missing)}")
    non_numeric = [col for col in df.columns if col in FEATURE_COLUMNS and not pd.api.types.is_numeric_dtype(df[col])]
    if non_numeric:
        warnings.append(f"Sayısal olmayan feature kolonları: {', '.join(non_numeric)}")
    return warnings


def _missing_summary(df: pd.DataFrame) -> dict[str, Any]:
    total = max(len(df), 1)
    return {
        col: {
            "missing_count": int(df[col].isna().sum()),
            "missing_ratio": float(df[col].isna().sum() / total),
        }
        for col in df.columns
    }


def save_feature_snapshot(
    conn: sqlite3.Connection,
    dataset: MLFeatureDataset,
    *,
    scope: dict | None = None,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> int:
    ensure_ml_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ml_feature_snapshots (
            feature_schema_version, scope_json, year, faculty_id, department_id,
            sample_count, feature_names_json, missing_features_summary_json,
            imputation_strategy_json, normalization_summary_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            dataset.feature_schema_version,
            _json(scope or {}),
            year,
            faculty_id,
            department_id,
            dataset.sample_count,
            _json(dataset.feature_names),
            _json(dataset.missing_features_summary),
            _json(dataset.imputation_strategy),
            _json(dataset.normalization_summary),
            _now(),
        ),
    )
    return int(cur.lastrowid)


def extract_features_for_course(conn: sqlite3.Connection, course_id: int, year: int) -> dict:
    dataset = build_course_feature_dataset(conn, year=year)
    if dataset.X.empty:
        return {}
    raw = _load_raw_course_rows(conn, year=year, faculty_id=None, department_id=None)
    if "ders_id" not in raw.columns:
        return {}
    raw = raw.reset_index(drop=True)
    matches = raw.index[raw["ders_id"].astype(int) == int(course_id)].tolist()
    if not matches:
        return {}
    idx = matches[0]
    return dataset.X.iloc[idx].to_dict()
