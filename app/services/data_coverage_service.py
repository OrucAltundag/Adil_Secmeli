# -*- coding: utf-8 -*-
# pyright: reportArgumentType=false, reportAttributeAccessIssue=false, reportGeneralTypeIssues=false, reportReturnType=false
# NOT: SQLAlchemy 1.4 stilinde Column[X] descriptor'lari Pylance tarafindan
# X plain tipiyle uyumsuz gorulur. Runtime'da descriptor __get__/set__
# uzerinden plain X dondurur — gercek uyumsuzluk yoktur. Pragma'lar yalnizca
# bu sahte uyarılari susturur, davranisi degistirmez.
"""
Data Coverage Reporting Service

Sistem-çapında veri kapsama oranlarını hesaplar ve raporlar.
Fakülte, bölüm ve yıl bazında coverage analizi yapar.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import (
    AnketSonuclari,
    Bolum,
    DataCoverageReport,
    Ders,
    Fakulte,
    Performans,
    Populerlik,
    Skor,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _json_dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def calculate_coverage_ratios(
    session: Session,
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
) -> dict:
    """
    Veri kapsama oranlarını hesapla.

    Returns:
        {
            'total_courses': int,
            'courses_with_criteria': int,
            'courses_with_performance': int,
            'courses_with_popularity': int,
            'courses_with_survey': int,
            'courses_with_score': int,
            'courses_with_trend_data': int,
            'criteria_ratio': float (0-1),
            'performance_ratio': float (0-1),
            ...
        }
    """
    try:
        # Base query
        q = session.query(Ders)

        if faculty_id:
            q = q.filter(Ders.fakulte_id == faculty_id)
        if department_id:
            q = q.filter(Ders.bolum_id == department_id)

        total_courses = q.count()
        if total_courses == 0:
            return {
                'total_courses': 0,
                'courses_with_criteria': 0,
                'courses_with_performance': 0,
                'courses_with_popularity': 0,
                'courses_with_survey': 0,
                'courses_with_score': 0,
                'courses_with_trend_data': 0,
                'criteria_ratio': 0.0,
                'performance_ratio': 0.0,
                'popularity_ratio': 0.0,
                'survey_ratio': 0.0,
                'score_ratio': 0.0,
                'trend_ratio': 0.0,
                'overall_score': 0.0,
            }

        course_ids = [c.ders_id for c in q]

        # Criteria (manuel SQL sorgusu - ders_kriterleri tablosu)
        try:
            from sqlalchemy import text as _sa_text
            courses_with_criteria = session.execute(
                _sa_text("SELECT COUNT(DISTINCT ders_id) FROM ders_kriterleri")
            ).scalar() or 0
        except Exception:
            courses_with_criteria = 0

        # Performance
        courses_with_performance = session.query(func.count(func.distinct(Performans.ders_id))).filter(
            Performans.ders_id.in_(course_ids) if course_ids else False,
            Performans.akademik_yil == year
        ).scalar() or 0

        # Popularity
        courses_with_popularity = session.query(func.count(func.distinct(Populerlik.ders_id))).filter(
            Populerlik.ders_id.in_(course_ids) if course_ids else False,
            Populerlik.akademik_yil == year
        ).scalar() or 0

        # Survey (anket_sonuclari)
        courses_with_survey = session.query(func.count(func.distinct(AnketSonuclari.ders_id))).filter(
            AnketSonuclari.ders_id.in_(course_ids) if course_ids else False
        ).scalar() or 0

        # Score
        courses_with_score = session.query(func.count(func.distinct(Skor.ders_id))).filter(
            Skor.ders_id.in_(course_ids) if course_ids else False,
            Skor.akademik_yil == year
        ).scalar() or 0

        # Trend (en az 2 yıl data)
        courses_with_trend_data = 0
        if course_ids:
            trend_q = session.query(Performans.ders_id, func.count()).filter(
                Performans.ders_id.in_(course_ids)
            ).group_by(Performans.ders_id).having(func.count() >= 2)
            courses_with_trend_data = trend_q.count()

        # Ratios
        criteria_ratio = courses_with_criteria / total_courses if total_courses > 0 else 0
        performance_ratio = courses_with_performance / total_courses if total_courses > 0 else 0
        popularity_ratio = courses_with_popularity / total_courses if total_courses > 0 else 0
        survey_ratio = courses_with_survey / total_courses if total_courses > 0 else 0
        score_ratio = courses_with_score / total_courses if total_courses > 0 else 0
        trend_ratio = courses_with_trend_data / total_courses if total_courses > 0 else 0

        # Overall coverage: ağırlıklı ortalama
        # Kriter en önemli (%40), sonra performance (%20), popularity (%20), survey (%10), score/trend (%5)
        overall_score = (
            criteria_ratio * 0.40 +
            performance_ratio * 0.20 +
            popularity_ratio * 0.15 +
            survey_ratio * 0.15 +
            score_ratio * 0.05 +
            trend_ratio * 0.05
        )

        return {
            'total_courses': total_courses,
            'courses_with_criteria': courses_with_criteria,
            'courses_with_performance': courses_with_performance,
            'courses_with_popularity': courses_with_popularity,
            'courses_with_survey': courses_with_survey,
            'courses_with_score': courses_with_score,
            'courses_with_trend_data': courses_with_trend_data,
            'criteria_ratio': round(criteria_ratio, 3),
            'performance_ratio': round(performance_ratio, 3),
            'popularity_ratio': round(popularity_ratio, 3),
            'survey_ratio': round(survey_ratio, 3),
            'score_ratio': round(score_ratio, 3),
            'trend_ratio': round(trend_ratio, 3),
            'overall_score': round(overall_score, 3),
        }
    except Exception as e:
        print(f"[DataCoverage] calculate_coverage_ratios hata: {e}")
        return {
            'total_courses': 0,
            'courses_with_criteria': 0,
            'courses_with_performance': 0,
            'courses_with_popularity': 0,
            'courses_with_survey': 0,
            'courses_with_score': 0,
            'courses_with_trend_data': 0,
            'criteria_ratio': 0.0,
            'performance_ratio': 0.0,
            'popularity_ratio': 0.0,
            'survey_ratio': 0.0,
            'score_ratio': 0.0,
            'trend_ratio': 0.0,
            'overall_score': 0.0,
        }


def generate_coverage_report(
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    session: Optional[Session] = None,
) -> DataCoverageReport:
    """
    Veri kapsama raporu oluştur ve kaydet.
    """
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        scope_type = "global"
        if faculty_id and department_id:
            scope_type = "department"
        elif faculty_id:
            scope_type = "faculty"

        # Calculate coverage
        coverage = calculate_coverage_ratios(session, year, faculty_id, department_id)

        # Generate recommendations
        recommendations = []
        if coverage['overall_score'] < 0.5:
            recommendations.append("Veri yetersiz. Karar verici olmayan ön değerlendirme olarak kullanın.")
        if coverage['criteria_ratio'] < 0.5:
            recommendations.append("Kriter verisi eksik. Bölüm başkanları ile iletişime geçin.")
        if coverage['performance_ratio'] < 0.3:
            recommendations.append("Performans verisi eksik. Ders etkinliği raporları kontrol edin.")
        if coverage['survey_ratio'] < 0.3:
            recommendations.append("Anket verisi eksik. Öğrenci feedbacki toplayın.")

        # Create report
        report = DataCoverageReport(
            scope_type=scope_type,
            faculty_id=faculty_id,
            department_id=department_id,
            year=year,
            semester=None,
            total_courses=coverage['total_courses'],
            courses_with_criteria=coverage['courses_with_criteria'],
            courses_with_performance=coverage['courses_with_performance'],
            courses_with_popularity=coverage['courses_with_popularity'],
            courses_with_survey=coverage['courses_with_survey'],
            courses_with_score=coverage['courses_with_score'],
            courses_with_trend_data=coverage['courses_with_trend_data'],
            criteria_coverage_ratio=coverage['criteria_ratio'],
            performance_coverage_ratio=coverage['performance_ratio'],
            popularity_coverage_ratio=coverage['popularity_ratio'],
            survey_coverage_ratio=coverage['survey_ratio'],
            score_coverage_ratio=coverage['score_ratio'],
            trend_coverage_ratio=coverage['trend_ratio'],
            overall_coverage_score=coverage['overall_score'],
            missing_data_summary_json=_json_dump({
                'no_criteria': coverage['total_courses'] - coverage['courses_with_criteria'],
                'no_performance': coverage['total_courses'] - coverage['courses_with_performance'],
                'no_popularity': coverage['total_courses'] - coverage['courses_with_popularity'],
                'no_survey': coverage['total_courses'] - coverage['courses_with_survey'],
            }),
            recommendations_json=_json_dump(recommendations),
            created_at=_now(),
        )
        session.add(report)
        session.commit()

        return report
    finally:
        if close_session:
            session.close()


def get_coverage_table(
    year: int,
    scope_type: str = "department",  # department, faculty, or both
    session: Optional[Session] = None,
) -> list[dict]:
    """
    Fakülte/bölüm bazında coverage table.

    Returns:
        [
            {
                'faculty_name': str,
                'department_name': str,
                'total_courses': int,
                'overall_coverage_score': float,
                'coverage_level': str,
                'recommendations': str,
            }
        ]
    """
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        results = []

        # Get all faculties
        faculties = session.query(Fakulte).all()

        for fak in faculties:
            if scope_type in ["faculty", "both"]:
                coverage = calculate_coverage_ratios(session, year, faculty_id=fak.fakulte_id)
                level = "low" if coverage['overall_score'] < 0.4 else "medium" if coverage['overall_score'] < 0.7 else "good"
                results.append({
                    'faculty_name': fak.ad,
                    'department_name': None,
                    'total_courses': coverage['total_courses'],
                    'overall_coverage_score': coverage['overall_score'],
                    'coverage_level': level,
                    'criteria_ratio': coverage['criteria_ratio'],
                })

            if scope_type in ["department", "both"]:
                departments = session.query(Bolum).filter(Bolum.fakulte_id == fak.fakulte_id).all()
                for dept in departments:
                    coverage = calculate_coverage_ratios(session, year, faculty_id=fak.fakulte_id, department_id=dept.bolum_id)
                    if coverage['total_courses'] > 0:
                        level = "low" if coverage['overall_score'] < 0.4 else "medium" if coverage['overall_score'] < 0.7 else "good"
                        results.append({
                            'faculty_name': fak.ad,
                            'department_name': dept.ad,
                            'total_courses': coverage['total_courses'],
                            'overall_coverage_score': coverage['overall_score'],
                            'coverage_level': level,
                            'criteria_ratio': coverage['criteria_ratio'],
                        })

        return results
    finally:
        if close_session:
            session.close()
