# -*- coding: utf-8 -*-
"""
Missing Data Detection & Management Service

Eksik veriyi tespit eder ve düşük güven kararları işaretler.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import (
    MissingDataItem, DataValidationIssue, LowConfidenceDecisionFlag,
    CourseDecision, Ders, Performans, Populerlik, AnketSonuclari, Skor
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def detect_missing_data_for_course(
    course_id: int,
    year: int,
    semester: str = "Güz",
    session: Optional[Session] = None,
) -> list[MissingDataItem]:
    """
    Bir ders için eksik veriyi tespit et.
    
    Kontrol edilen veriler:
    - success_rate (Performans)
    - capacity (Populerlik)
    - enrollment (Populerlik)
    - survey_count (AnketSonuclari)
    - trend_history (eski yıllar Performans)
    - score (Skor)
    """
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False
    
    try:
        course = session.query(Ders).filter(Ders.ders_id == course_id).first()
        if not course:
            return []
        
        missing_items = []
        faculty_id = course.fakulte_id
        department_id = course.bolum_id
        
        # Check Performans
        perf = session.query(Performans).filter(
            Performans.ders_id == course_id,
            Performans.akademik_yil == year,
            Performans.donem == semester
        ).first()
        
        if not perf or perf.basari_orani is None:
            item = MissingDataItem(
                course_id=course_id,
                year=year,
                semester=semester,
                faculty_id=faculty_id,
                department_id=department_id,
                missing_field="success_rate",
                severity="warning",
                required_for_decision=True,
                message=f"{course.ad}: Başarı oranı verisi yok.",
                suggested_action="Ders yöneticisine başarı oranı raporunu isteyin.",
                detected_at=_now(),
            )
            missing_items.append(item)
        
        # Check Populerlik / Capacity
        pop = session.query(Populerlik).filter(
            Populerlik.ders_id == course_id,
            Populerlik.akademik_yil == year,
            Populerlik.donem == semester
        ).first()
        
        if not pop or pop.kontenjan is None:
            item = MissingDataItem(
                course_id=course_id,
                year=year,
                semester=semester,
                faculty_id=faculty_id,
                department_id=department_id,
                missing_field="capacity",
                severity="info",
                required_for_decision=False,
                message=f"{course.ad}: Kontenjan verisi yok.",
                suggested_action="Ders yöneticisine sorun.",
                detected_at=_now(),
            )
            missing_items.append(item)
        
        if not pop or pop.talep_sayisi is None:
            item = MissingDataItem(
                course_id=course_id,
                year=year,
                semester=semester,
                faculty_id=faculty_id,
                department_id=department_id,
                missing_field="enrollment",
                severity="info",
                required_for_decision=False,
                message=f"{course.ad}: Talep sayısı verisi yok.",
                suggested_action="Önceki yıllar verisi kontrol edin.",
                detected_at=_now(),
            )
            missing_items.append(item)
        
        # Check Survey
        survey = session.query(AnketSonuclari).filter(
            AnketSonuclari.ders_id == course_id
        ).first()
        
        if not survey or survey.oy_sayisi is None or survey.oy_sayisi == 0:
            item = MissingDataItem(
                course_id=course_id,
                year=year,
                semester=semester,
                faculty_id=faculty_id,
                department_id=department_id,
                missing_field="survey_count",
                severity="warning",
                required_for_decision=False,
                message=f"{course.ad}: Anket verisi yok veya cevap sayısı 0.",
                suggested_action="Dersin başında anket uygulanmalı.",
                detected_at=_now(),
            )
            missing_items.append(item)
        
        # Check Score
        score = session.query(Skor).filter(
            Skor.ders_id == course_id,
            Skor.akademik_yil == year,
            Skor.donem == semester
        ).first()
        
        if not score or score.skor_top is None:
            item = MissingDataItem(
                course_id=course_id,
                year=year,
                semester=semester,
                faculty_id=faculty_id,
                department_id=department_id,
                missing_field="score",
                severity="critical",
                required_for_decision=True,
                message=f"{course.ad}: Hesaplanan skor yok.",
                suggested_action="Karar motorunu çalıştırın.",
                detected_at=_now(),
            )
            missing_items.append(item)
        
        # Check Trend (en az 2 yıl data)
        years_of_data = session.query(Performans.akademik_yil).filter(
            Performans.ders_id == course_id
        ).distinct().count()
        
        if years_of_data < 2:
            item = MissingDataItem(
                course_id=course_id,
                year=year,
                semester=semester,
                faculty_id=faculty_id,
                department_id=department_id,
                missing_field="trend_history",
                severity="info",
                required_for_decision=False,
                message=f"{course.ad}: Trend analizi için yetersiz veriye sahip (sadece {years_of_data} yıl).",
                suggested_action="Eski yıllar data toplayın.",
                detected_at=_now(),
            )
            missing_items.append(item)
        
        # Save all items
        for item in missing_items:
            session.add(item)
        session.commit()
        
        return missing_items
    finally:
        if close_session:
            session.close()


def record_low_confidence_decision(
    decision_run_id: int,
    course_decision_id: Optional[int],
    course_id: int,
    year: int,
    confidence_score: float,
    confidence_level: str,
    reason: str,
    session: Optional[Session] = None,
) -> LowConfidenceDecisionFlag:
    """
    Düşük güven kararını işaretle.
    """
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False
    
    try:
        flag = LowConfidenceDecisionFlag(
            decision_run_id=decision_run_id,
            course_decision_id=course_decision_id,
            course_id=course_id,
            year=year,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            reason=reason,
            recommended_action="Bu karar destek amaçlı değerlendirilmelidir.",
            created_at=_now(),
        )
        session.add(flag)
        session.commit()
        return flag
    finally:
        if close_session:
            session.close()


def record_validation_issue(
    source_type: str,
    issue_type: str,
    severity: str,
    message: str,
    source_id: Optional[int] = None,
    source_row_id: Optional[int] = None,
    course_id: Optional[int] = None,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    year: Optional[int] = None,
    field_name: Optional[str] = None,
    raw_value: Optional[str] = None,
    session: Optional[Session] = None,
) -> DataValidationIssue:
    """
    Veri validation issue'sunu kaydet.
    """
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False
    
    try:
        issue = DataValidationIssue(
            source_type=source_type,
            source_id=source_id,
            source_row_id=source_row_id,
            course_id=course_id,
            faculty_id=faculty_id,
            department_id=department_id,
            year=year,
            field_name=field_name,
            issue_type=issue_type,
            severity=severity,
            message=message,
            raw_value=raw_value,
            is_resolved=False,
            created_at=_now(),
        )
        session.add(issue)
        session.commit()
        return issue
    finally:
        if close_session:
            session.close()


def get_missing_data_matrix(
    year: int,
    faculty_id: Optional[int] = None,
    session: Optional[Session] = None,
) -> list[dict]:
    """
    Eksik veri matrisini döndür.
    
    Returns:
        [
            {
                'course_code': str,
                'course_name': str,
                'missing_fields': [str],
                'critical_count': int,
                'warning_count': int,
                'total_missing': int,
                'data_quality': str,
            }
        ]
    """
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False
    
    try:
        # Get all missing items for year/faculty
        q = session.query(MissingDataItem).filter(
            MissingDataItem.year == year,
            MissingDataItem.resolved_at.is_(None)
        )
        
        if faculty_id:
            q = q.filter(MissingDataItem.faculty_id == faculty_id)
        
        items = q.all()
        
        # Group by course
        by_course = {}
        for item in items:
            course_id = item.course_id
            if course_id not in by_course:
                by_course[course_id] = {
                    'missing_fields': [],
                    'critical': 0,
                    'warning': 0,
                    'info': 0,
                }
            by_course[course_id]['missing_fields'].append(item.missing_field)
            if item.severity == 'critical':
                by_course[course_id]['critical'] += 1
            elif item.severity == 'warning':
                by_course[course_id]['warning'] += 1
            else:
                by_course[course_id]['info'] += 1
        
        # Build matrix
        matrix = []
        for course_id, data in by_course.items():
            course = session.query(Ders).filter(Ders.ders_id == course_id).first()
            if course:
                total_missing = len(data['missing_fields'])
                quality = "good" if total_missing == 0 else "medium" if total_missing <= 2 else "poor"
                
                matrix.append({
                    'course_code': course.kod or "",
                    'course_name': course.ad,
                    'course_id': course_id,
                    'missing_fields': data['missing_fields'],
                    'critical_count': data['critical'],
                    'warning_count': data['warning'],
                    'info_count': data['info'],
                    'total_missing': total_missing,
                    'data_quality': quality,
                })
        
        return sorted(matrix, key=lambda x: x['total_missing'], reverse=True)
    finally:
        if close_session:
            session.close()
