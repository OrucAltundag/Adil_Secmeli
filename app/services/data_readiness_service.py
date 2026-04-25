# -*- coding: utf-8 -*-
"""
Data Readiness Assessment Service

Sistem'in karar vermeye ne kadar hazır olduğunu değerlendirir.
Veri olgunluğu seviyelerini hesaplar ve raporlar.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import DataReadinessAssessment, DataCoverageReport, DataValidationIssue
from app.services.data_coverage_service import calculate_coverage_ratios


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _json_dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def calculate_readiness_score(
    session: Session,
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
) -> dict:
    """
    Veri olgunluğu skorunu hesapla (0-100).
    
    Bileşenler:
    - Coverage score (40%)
    - Performance coverage (15%)
    - Popularity coverage (15%)
    - Survey coverage (15%)
    - Validation quality (10%)
    - Data confidence average (5%)
    
    Returns:
        {
            'readiness_score': float (0-100),
            'readiness_level': str,
            'criteria_score': float,
            'performance_score': float,
            'popularity_score': float,
            'survey_score': float,
            'validation_score': float,
            'confidence_average': float,
            'blocking_issues': int,
            'warning_issues': int,
        }
    """
    try:
        # Get coverage
        coverage = calculate_coverage_ratios(session, year, faculty_id, department_id)
        
        # Map ratios to scores
        criteria_score = coverage['criteria_ratio'] * 100
        performance_score = coverage['performance_ratio'] * 100
        popularity_score = coverage['popularity_ratio'] * 100
        survey_score = coverage['survey_ratio'] * 100
        trend_score = coverage['trend_ratio'] * 100
        
        # Count validation issues
        q = session.query(DataValidationIssue)
        if faculty_id:
            q = q.filter(DataValidationIssue.faculty_id == faculty_id)
        if department_id:
            q = q.filter(DataValidationIssue.department_id == department_id)
        
        all_issues = q.all()
        blocking_issues = len([i for i in all_issues if i.severity == "critical" and not i.is_resolved])
        warning_issues = len([i for i in all_issues if i.severity in ["warning", "error"] and not i.is_resolved])
        
        # Validation quality score: no blocking issues = 100, each blocking = -25
        validation_score = max(0, 100 - (blocking_issues * 25))
        
        # Data confidence average (placeholder - default 0.5 if no data)
        data_confidence_average = 0.5
        
        # Composite readiness score
        readiness_score = (
            criteria_score * 0.40 +
            performance_score * 0.15 +
            popularity_score * 0.15 +
            survey_score * 0.15 +
            validation_score * 0.10 +
            (data_confidence_average * 100) * 0.05
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
            'criteria_score': round(criteria_score, 1),
            'performance_score': round(performance_score, 1),
            'popularity_score': round(popularity_score, 1),
            'survey_score': round(survey_score, 1),
            'trend_score': round(trend_score, 1),
            'validation_score': round(validation_score, 1),
            'data_confidence_average': round(data_confidence_average, 2),
            'blocking_issues': blocking_issues,
            'warning_issues': warning_issues,
            'total_courses': coverage['total_courses'],
        }
    except Exception as e:
        print(f"[DataReadiness] calculate_readiness_score hata: {e}")
        return {
            'readiness_score': 0.0,
            'readiness_level': 'not_ready',
            'criteria_score': 0.0,
            'performance_score': 0.0,
            'popularity_score': 0.0,
            'survey_score': 0.0,
            'trend_score': 0.0,
            'validation_score': 0.0,
            'data_confidence_average': 0.0,
            'blocking_issues': 0,
            'warning_issues': 0,
            'total_courses': 0,
        }


def assess_data_readiness(
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    session: Optional[Session] = None,
) -> DataReadinessAssessment:
    """
    Veri olgunluğu değerlendirmesi yap ve kaydet.
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
        
        # Calculate readiness
        readiness = calculate_readiness_score(session, year, faculty_id, department_id)
        
        # Generate recommendations
        recommendations = []
        if readiness['readiness_level'] in ['not_ready', 'low']:
            recommendations.append("Veri olgunluğu düşük. Karar sistemi destek amaçlı kullanılmalıdır.")
            if readiness['criteria_score'] < 40:
                recommendations.append("Öncelik 1: Kriter verisi tamamlanmalı.")
            if readiness['performance_score'] < 40:
                recommendations.append("Öncelik 2: Performans verisi tamamlanmalı.")
            if readiness['survey_score'] < 40:
                recommendations.append("Öncelik 3: Anket verisi toplanmalı.")
        
        if readiness['blocking_issues'] > 0:
            recommendations.append(f"{readiness['blocking_issues']} kritik validation issue var. Çözülmeli.")
        
        # Create assessment
        assessment = DataReadinessAssessment(
            scope_type=scope_type,
            faculty_id=faculty_id,
            department_id=department_id,
            year=year,
            readiness_score=readiness['readiness_score'],
            readiness_level=readiness['readiness_level'],
            criteria_coverage_score=readiness['criteria_score'],
            performance_coverage_score=readiness['performance_score'],
            popularity_coverage_score=readiness['popularity_score'],
            survey_coverage_score=readiness['survey_score'],
            trend_readiness_score=readiness['trend_score'],
            validation_quality_score=readiness['validation_score'],
            data_confidence_average=readiness['data_confidence_average'],
            blocking_issues_count=readiness['blocking_issues'],
            warning_issues_count=readiness['warning_issues'],
            recommendation_summary='\n'.join(recommendations) if recommendations else None,
            created_at=_now(),
        )
        session.add(assessment)
        session.commit()
        
        return assessment
    finally:
        if close_session:
            session.close()


def get_readiness_level(score: float) -> str:
    """Score'dan readiness level'ı belirle."""
    if score < 30:
        return "not_ready"
    elif score < 50:
        return "low"
    elif score < 70:
        return "medium"
    elif score < 85:
        return "good"
    else:
        return "decision_ready"


def get_blocking_reasons(
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    session: Optional[Session] = None,
) -> list[str]:
    """Readiness'i bloklayan sebepleri listele."""
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False
    
    try:
        readiness = calculate_readiness_score(session, year, faculty_id, department_id)
        reasons = []
        
        if readiness['blocking_issues'] > 0:
            reasons.append(f"Kritik validation issues: {readiness['blocking_issues']}")
        
        if readiness['total_courses'] == 0:
            reasons.append("Hiç ders yok")
            return reasons
        
        if readiness['criteria_score'] < 30:
            reasons.append("Kriter verisi kritik olarak eksik (<30%)")
        
        if readiness['validation_score'] < 50:
            reasons.append("Validation kalitesi düşük")
        
        return reasons
    finally:
        if close_session:
            session.close()
