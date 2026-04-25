# -*- coding: utf-8 -*-
"""
Data Quality Integration Service

Veri kalitesi servislerinin sqlite3 cursor tabanlı wrapperları.
Decision engine ile entegrasyon için cursor-safe fonksiyonlar sağlar.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def assess_data_readiness_cursor(
    cur: sqlite3.Cursor,
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    semester: Optional[str] = None,
) -> dict[str, Any]:
    """
    Veri olgunluğunu değerlendir (cursor tabanlı).
    
    Returns:
        {
            'readiness_score': float (0-100),
            'readiness_level': str ('not_ready', 'low', 'medium', 'good', 'decision_ready'),
            'total_courses': int,
            'criteria_score': float,
            'performance_score': float,
            'popularity_score': float,
            'survey_score': float,
            'validation_score': float,
        }
    """
    try:
        # Toplam ders sayısı
        where_fac = f"AND d.fakulte_id = {int(faculty_id)}" if faculty_id else ""
        where_dept = f"AND d.bolum_id = {int(department_id)}" if department_id else ""
        
        cur.execute(f"SELECT COUNT(*) FROM ders d WHERE 1=1 {where_fac} {where_dept}")
        total_courses = int(cur.fetchone()[0] or 0)
        
        if total_courses == 0:
            return {
                'readiness_score': 0.0,
                'readiness_level': 'not_ready',
                'total_courses': 0,
                'criteria_score': 0.0,
                'performance_score': 0.0,
                'popularity_score': 0.0,
                'survey_score': 0.0,
                'validation_score': 100.0,  # No issues means good score
            }
        
        # Criteria coverage (ders_kriterleri tablosu)
        try:
            cur.execute("SELECT COUNT(DISTINCT ders_id) FROM ders_kriterleri")
            criteria_count = int(cur.fetchone()[0] or 0)
        except sqlite3.OperationalError:
            criteria_count = 0
        
        # Performance coverage
        try:
            cur.execute(f"""
                SELECT COUNT(DISTINCT ders_id) FROM performans 
                WHERE akademik_yil = {int(year)} AND basari_orani IS NOT NULL
            """)
            perf_count = int(cur.fetchone()[0] or 0)
        except sqlite3.OperationalError:
            perf_count = 0
        
        # Popularity coverage
        try:
            cur.execute(f"""
                SELECT COUNT(DISTINCT ders_id) FROM populerlik 
                WHERE akademik_yil = {int(year)} AND doluluk_orani IS NOT NULL
            """)
            pop_count = int(cur.fetchone()[0] or 0)
        except sqlite3.OperationalError:
            pop_count = 0
        
        # Survey coverage
        try:
            cur.execute("SELECT COUNT(DISTINCT ders_id) FROM anket_sonuclari WHERE oy_sayisi > 0")
            survey_count = int(cur.fetchone()[0] or 0)
        except sqlite3.OperationalError:
            survey_count = 0
        
        # Validation issues
        try:
            cur.execute("""
                SELECT COUNT(*) FROM data_validation_issues 
                WHERE severity = 'critical' AND is_resolved = 0
            """)
            blocking_issues = int(cur.fetchone()[0] or 0)
        except sqlite3.OperationalError:
            blocking_issues = 0
        
        # Calculate ratios
        criteria_score = (criteria_count / total_courses * 100) if total_courses > 0 else 0
        performance_score = (perf_count / total_courses * 100) if total_courses > 0 else 0
        popularity_score = (pop_count / total_courses * 100) if total_courses > 0 else 0
        survey_score = (survey_count / total_courses * 100) if total_courses > 0 else 0
        validation_score = max(0, 100 - (blocking_issues * 25))  # -25 per blocking issue
        
        # Composite readiness score (weighting)
        readiness_score = (
            criteria_score * 0.40 +
            performance_score * 0.15 +
            popularity_score * 0.15 +
            survey_score * 0.15 +
            validation_score * 0.15
        )
        
        # Determine level
        if readiness_score < 30:
            level = "not_ready"
        elif readiness_score < 50:
            level = "low"
        elif readiness_score < 70:
            level = "medium"
        elif readiness_score < 85:
            level = "good"
        else:
            level = "decision_ready"
        
        return {
            'readiness_score': round(readiness_score, 1),
            'readiness_level': level,
            'total_courses': total_courses,
            'criteria_score': round(criteria_score, 1),
            'performance_score': round(performance_score, 1),
            'popularity_score': round(popularity_score, 1),
            'survey_score': round(survey_score, 1),
            'validation_score': round(validation_score, 1),
        }
    except Exception as e:
        return {
            'readiness_score': 0.0,
            'readiness_level': 'not_ready',
            'total_courses': 0,
            'criteria_score': 0.0,
            'performance_score': 0.0,
            'popularity_score': 0.0,
            'survey_score': 0.0,
            'validation_score': 0.0,
            'error': str(e),
        }


def generate_coverage_report_cursor(
    cur: sqlite3.Cursor,
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    semester: Optional[str] = None,
) -> dict[str, Any]:
    """
    Veri kapsama raporunu hesapla (cursor tabanlı).
    
    Returns:
        {
            'total_courses': int,
            'courses_with_criteria': int,
            'courses_with_performance': int,
            'courses_with_popularity': int,
            'courses_with_survey': int,
            'coverage_percentage': float (0-100),
            'by_faculty': {...},
            'by_department': {...},
        }
    """
    try:
        where_fac = f"AND d.fakulte_id = {int(faculty_id)}" if faculty_id else ""
        where_dept = f"AND d.bolum_id = {int(department_id)}" if department_id else ""
        
        cur.execute(f"SELECT COUNT(*) FROM ders d WHERE 1=1 {where_fac} {where_dept}")
        total_courses = int(cur.fetchone()[0] or 0)
        
        if total_courses == 0:
            return {
                'total_courses': 0,
                'courses_with_criteria': 0,
                'courses_with_performance': 0,
                'courses_with_popularity': 0,
                'courses_with_survey': 0,
                'coverage_percentage': 0.0,
            }
        
        # Count courses with each data type
        try:
            cur.execute("SELECT COUNT(DISTINCT ders_id) FROM ders_kriterleri")
            with_criteria = int(cur.fetchone()[0] or 0)
        except:
            with_criteria = 0
        
        try:
            cur.execute(f"""
                SELECT COUNT(DISTINCT ders_id) FROM performans 
                WHERE akademik_yil = {int(year)} AND basari_orani IS NOT NULL
            """)
            with_perf = int(cur.fetchone()[0] or 0)
        except:
            with_perf = 0
        
        try:
            cur.execute(f"""
                SELECT COUNT(DISTINCT ders_id) FROM populerlik 
                WHERE akademik_yil = {int(year)} AND kontenjan IS NOT NULL
            """)
            with_pop = int(cur.fetchone()[0] or 0)
        except:
            with_pop = 0
        
        try:
            cur.execute("SELECT COUNT(DISTINCT ders_id) FROM anket_sonuclari")
            with_survey = int(cur.fetchone()[0] or 0)
        except:
            with_survey = 0
        
        # Coverage percentage: weighted average
        coverage = (
            (with_criteria / total_courses * 0.40 if total_courses > 0 else 0) +
            (with_perf / total_courses * 0.25 if total_courses > 0 else 0) +
            (with_pop / total_courses * 0.20 if total_courses > 0 else 0) +
            (with_survey / total_courses * 0.15 if total_courses > 0 else 0)
        ) * 100
        
        return {
            'total_courses': total_courses,
            'courses_with_criteria': with_criteria,
            'courses_with_performance': with_perf,
            'courses_with_popularity': with_pop,
            'courses_with_survey': with_survey,
            'coverage_percentage': round(coverage, 1),
        }
    except Exception as e:
        return {
            'total_courses': 0,
            'courses_with_criteria': 0,
            'courses_with_performance': 0,
            'courses_with_popularity': 0,
            'courses_with_survey': 0,
            'coverage_percentage': 0.0,
            'error': str(e),
        }


def save_data_coverage_report(
    cur: sqlite3.Cursor,
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    semester: Optional[str] = None,
    coverage_data: Optional[dict[str, Any]] = None,
) -> int:
    """
    Kapsama raporunu data_coverage_reports tablosuna kaydet.
    
    Returns:
        Report ID
    """
    if coverage_data is None:
        coverage_data = generate_coverage_report_cursor(cur, year, faculty_id, department_id, semester)
    
    try:
        cur.execute(
            """
            INSERT INTO data_coverage_reports (
                year, faculty_id, department_id, semester,
                total_courses, courses_with_criteria, courses_with_performance,
                courses_with_popularity, courses_with_survey,
                coverage_percentage, report_json, generated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(year),
                int(faculty_id) if faculty_id else None,
                int(department_id) if department_id else None,
                str(semester) if semester else None,
                coverage_data.get('total_courses', 0),
                coverage_data.get('courses_with_criteria', 0),
                coverage_data.get('courses_with_performance', 0),
                coverage_data.get('courses_with_popularity', 0),
                coverage_data.get('courses_with_survey', 0),
                float(coverage_data.get('coverage_percentage', 0.0)),
                _json_dump(coverage_data),
                _now(),
            ),
        )
        return int(cur.lastrowid)
    except sqlite3.OperationalError:
        # Table might not exist - create it
        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS data_coverage_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER NOT NULL,
                    faculty_id INTEGER,
                    department_id INTEGER,
                    semester TEXT,
                    total_courses INTEGER,
                    courses_with_criteria INTEGER,
                    courses_with_performance INTEGER,
                    courses_with_popularity INTEGER,
                    courses_with_survey INTEGER,
                    coverage_percentage REAL,
                    report_json TEXT,
                    generated_at TEXT
                )
            """)
            cur.execute(
                """
                INSERT INTO data_coverage_reports (
                    year, faculty_id, department_id, semester,
                    total_courses, courses_with_criteria, courses_with_performance,
                    courses_with_popularity, courses_with_survey,
                    coverage_percentage, report_json, generated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(year),
                    int(faculty_id) if faculty_id else None,
                    int(department_id) if department_id else None,
                    str(semester) if semester else None,
                    coverage_data.get('total_courses', 0),
                    coverage_data.get('courses_with_criteria', 0),
                    coverage_data.get('courses_with_performance', 0),
                    coverage_data.get('courses_with_popularity', 0),
                    coverage_data.get('courses_with_survey', 0),
                    float(coverage_data.get('coverage_percentage', 0.0)),
                    _json_dump(coverage_data),
                    _now(),
                ),
            )
            return int(cur.lastrowid)
        except Exception:
            return 0
