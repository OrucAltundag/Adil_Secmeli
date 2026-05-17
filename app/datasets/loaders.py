"""Real dataset loaders from CSV and SQLite sources."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import resolve_sqlite_db_path
from app.datasets.entities import DatasetBundle


class RealDatasetLoader:
    """Load canonical tables from real data sources."""

    REQUIRED_TABLES = ("students", "courses", "preferences")
    OPTIONAL_TABLES = ("survey_responses", "allocations")

    def __init__(self, dataset_name: str = "real_dataset") -> None:
        self.dataset_name = dataset_name

    def from_csv_folder(self, folder_path: str | os.PathLike[str]) -> DatasetBundle:
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"Dataset folder not found: {folder}")

        data: dict[str, pd.DataFrame] = {}
        for table in (*self.REQUIRED_TABLES, *self.OPTIONAL_TABLES):
            csv_path = folder / f"{table}.csv"
            if not csv_path.exists():
                if table in self.REQUIRED_TABLES:
                    raise FileNotFoundError(f"Missing required table file: {csv_path}")
                continue
            data[table] = pd.read_csv(csv_path)

        self._validate_tables(data)
        return DatasetBundle(
            dataset_name=self.dataset_name,
            raw_real=data,
            metadata={"source_type": "csv", "source_path": str(folder)},
        )

    def from_sqlite(self, db_path: str | os.PathLike[str]) -> DatasetBundle:
        db_file = resolve_sqlite_db_path(db_path)
        if not db_file.exists():
            raise FileNotFoundError(f"SQLite DB not found: {db_file}")

        conn = sqlite3.connect(str(db_file))
        try:
            raw_real = {
                "students": self._load_students(conn),
                "courses": self._load_courses(conn),
                "preferences": self._load_preferences(conn),
                "survey_responses": self._load_survey(conn),
                "allocations": self._load_allocations(conn),
            }
        finally:
            conn.close()

        cleaned = {name: df for name, df in raw_real.items() if not df.empty}
        self._validate_tables(cleaned)
        return DatasetBundle(
            dataset_name=self.dataset_name,
            raw_real=cleaned,
            metadata={"source_type": "sqlite", "source_path": str(db_file)},
        )

    def _validate_tables(self, tables: dict[str, pd.DataFrame]) -> None:
        for req in self.REQUIRED_TABLES:
            if req not in tables or tables[req].empty:
                raise ValueError(f"Required table '{req}' is missing or empty.")

    def _load_students(self, conn: sqlite3.Connection) -> pd.DataFrame:
        query = """
            SELECT
                o.ogr_id AS student_id,
                o.fakulte_id AS faculty_id,
                d.bolum_id AS department_id,
                NULL AS gender,
                NULL AS term,
                NULL AS gpa
            FROM ogrenci o
            LEFT JOIN bolum d ON d.fakulte_id = o.fakulte_id
        """
        return pd.read_sql_query(query, conn).drop_duplicates(subset=["student_id"])

    def _load_courses(self, conn: sqlite3.Connection) -> pd.DataFrame:
        query = """
            SELECT
                ders_id AS course_id,
                kod AS code,
                ad AS name,
                fakulte_id AS faculty_id,
                bolum_id AS department_id,
                kontenjan AS capacity,
                NULL AS difficulty_score,
                NULL AS instructor_effect_score
            FROM ders
        """
        return pd.read_sql_query(query, conn).drop_duplicates(subset=["course_id"])

    def _load_preferences(self, conn: sqlite3.Connection) -> pd.DataFrame:
        query = """
            SELECT
                ogr_id AS student_id,
                ders_id AS course_id,
                COALESCE(rank, 1) AS rank,
                puan AS preference_score
            FROM anket_cevap
        """
        df = pd.read_sql_query(query, conn)
        if df.empty:
            return pd.DataFrame(columns=["student_id", "course_id", "rank", "preference_score"])
        return df

    def _load_survey(self, conn: sqlite3.Connection) -> pd.DataFrame:
        query = """
            SELECT
                ogr_id AS student_id,
                ders_id AS course_id,
                puan AS satisfaction,
                siddet AS contribution,
                puan AS general_sentiment
            FROM anket_cevap
        """
        return pd.read_sql_query(query, conn)

    def _load_allocations(self, conn: sqlite3.Connection) -> pd.DataFrame:
        query = """
            SELECT
                ogr_id AS student_id,
                ders_id AS course_id,
                1 AS allocated,
                NULL AS rank_received
            FROM kayit
        """
        return pd.read_sql_query(query, conn)


def ensure_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for column in columns:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    return out


def ensure_non_negative(df: pd.DataFrame, columns: list[str], fill_value: float = 0.0) -> pd.DataFrame:
    out = df.copy()
    for column in columns:
        if column not in out.columns:
            continue
        out[column] = pd.to_numeric(out[column], errors="coerce").fillna(fill_value).clip(lower=0.0)
    return out


def sanitize_dataset(bundle: DatasetBundle) -> DatasetBundle:
    """Run minimal schema-safe clean-up before feature engineering."""
    raw = dict(bundle.raw_real)
    if "students" in raw:
        raw["students"] = ensure_numeric(raw["students"], ["student_id", "faculty_id", "department_id", "gpa"])
    if "courses" in raw:
        raw["courses"] = ensure_numeric(
            raw["courses"],
            ["course_id", "faculty_id", "department_id", "capacity", "difficulty_score", "instructor_effect_score"],
        )
        raw["courses"] = ensure_non_negative(raw["courses"], ["capacity"], fill_value=0.0)
    if "preferences" in raw:
        raw["preferences"] = ensure_numeric(raw["preferences"], ["student_id", "course_id", "rank", "preference_score"])
        raw["preferences"] = ensure_non_negative(raw["preferences"], ["rank"], fill_value=1.0)
    return DatasetBundle(
        dataset_name=bundle.dataset_name,
        raw_real=raw,
        derived=dict(bundle.derived),
        synthetic=dict(bundle.synthetic),
        metadata=dict(bundle.metadata),
    )

