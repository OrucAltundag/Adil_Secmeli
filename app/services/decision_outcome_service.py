# -*- coding: utf-8 -*-
# pyright: reportArgumentType=false, reportAttributeAccessIssue=false, reportGeneralTypeIssues=false, reportReturnType=false, reportOptionalMemberAccess=false
# NOT: SQLAlchemy 1.4 stilinde Column[X] descriptor'lari Pylance tarafindan
# X plain tipiyle uyumsuz gorulur. Runtime'da descriptor __get__/set__
# uzerinden plain X dondurur — gercek uyumsuzluk yoktur. Pragma'lar yalnizca
# bu sahte uyarılari susturur, davranisi degistirmez.
"""
Post-Decision Outcome Tracking Service

Karar sonrası gerçekleşen sonuçları izler ve değerlendirir.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import (
    CourseDecision,
    Performans,
    Populerlik,
    PostDecisionOutcome,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def record_post_decision_outcome(
    course_id: int,
    decision_year: int,
    outcome_year: int,
    actual_enrollment: Optional[int] = None,
    actual_capacity: Optional[int] = None,
    actual_success_rate: Optional[float] = None,
    actual_average_grade: Optional[float] = None,
    actual_survey_demand: Optional[int] = None,
    decision_run_id: Optional[int] = None,
    course_decision_id: Optional[int] = None,
    session: Optional[Session] = None,
) -> PostDecisionOutcome:
    """
    Karar sonrası outcome kaydedilir.

    Karar verilen yılda (decision_year) ders için alınan karar sonrası,
    sonraki yıl(lar)da (outcome_year) gerçekleşen sonuçlar kaydedilir.
    """
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        outcome = PostDecisionOutcome(
            decision_run_id=decision_run_id,
            course_decision_id=course_decision_id,
            course_id=course_id,
            decision_year=decision_year,
            outcome_year=outcome_year,
            actual_enrollment=actual_enrollment,
            actual_capacity=actual_capacity,
            actual_fill_rate=(actual_enrollment / actual_capacity) if (actual_capacity and actual_capacity > 0 and actual_enrollment is not None) else None,
            actual_success_rate=actual_success_rate,
            actual_average_grade=actual_average_grade,
            actual_survey_demand=actual_survey_demand,
            created_at=_now(),
        )
        session.add(outcome)
        session.commit()

        return outcome
    finally:
        if close_session:
            session.close()


def evaluate_decision_effectiveness(
    course_decision_id: int,
    session: Optional[Session] = None,
) -> dict:
    """
    Bir kararın sonraki yıl ne kadar etkili olduğunu değerlendir.

    Returns:
        {
            'decision_id': int,
            'course_id': int,
            'decision_year': int,
            'effectiveness_label': str,  # improved, worsened, stable
            'effectiveness_score': float,  # 0-1
            'explanation': str,
        }
    """
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        cd = session.query(CourseDecision).filter(
            CourseDecision.id == course_decision_id
        ).first()

        if not cd:
            return {
                'decision_id': course_decision_id,
                'effectiveness_label': 'unknown',
                'effectiveness_score': 0.0,
                'explanation': 'Karar bulunamadı',
            }

        # Get outcome from next year
        outcome = session.query(PostDecisionOutcome).filter(
            PostDecisionOutcome.course_decision_id == course_decision_id,
            PostDecisionOutcome.outcome_year > cd.year
        ).first()

        if not outcome:
            return {
                'decision_id': course_decision_id,
                'course_id': cd.course_id,
                'decision_year': cd.year,
                'effectiveness_label': 'unknown',
                'effectiveness_score': 0.0,
                'explanation': 'Henüz outcome verisi yok',
            }

        # Compare with decision and calculate effectiveness
        # NOT: Asagidaki satir tarihsel olarak kullanilmiyor (muhtemelen yarim kalmis
        # bir hesaplamanin kalintisi). Davranis korunarak yalnizca uyari susturuluyor.
        _ = cd.topsis_score or 0
        fill_rate = outcome.actual_fill_rate or 0
        success_rate = outcome.actual_success_rate or 0

        # Effectiveness: pozitif sonuçlar
        effectiveness_score = 0.0
        factors = []

        if fill_rate > 0.7:
            effectiveness_score += 0.3
            factors.append("Yüksek doluluk")
        elif fill_rate > 0.5:
            effectiveness_score += 0.15
            factors.append("Orta doluluk")

        if success_rate > 0.7:
            effectiveness_score += 0.3
            factors.append("Yüksek başarı")
        elif success_rate > 0.5:
            effectiveness_score += 0.15
            factors.append("Orta başarı")

        if outcome.actual_survey_demand and outcome.actual_survey_demand > 0:
            effectiveness_score += 0.2
            factors.append("Talep var")

        # Determine label
        if effectiveness_score > 0.6:
            label = "improved"
            explanation = "Karar başarılı: " + ", ".join(factors)
        elif effectiveness_score > 0.3:
            label = "stable"
            explanation = "Karar orta seviye etkili: " + ", ".join(factors) if factors else "Sınırlı veri"
        else:
            label = "worsened"
            explanation = "Karar az etkili olmuş"

        return {
            'decision_id': course_decision_id,
            'course_id': cd.course_id,
            'decision_year': cd.year,
            'outcome_year': outcome.outcome_year,
            'effectiveness_label': label,
            'effectiveness_score': round(float(effectiveness_score or 0), 2),
            'fill_rate': round(float(fill_rate or 0), 2),
            'success_rate': round(float(success_rate or 0), 2),
            'explanation': explanation,
        }
    finally:
        if close_session:
            session.close()


def compare_predicted_vs_actual(
    course_id: int,
    decision_year: int,
    outcome_year: int,
    session: Optional[Session] = None,
) -> dict:
    """
    Tahmin edilen vs gerçekleşen sonuçları karşılaştır.
    """
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        # Get decision
        cd = session.query(CourseDecision).filter(
            CourseDecision.course_id == course_id,
            CourseDecision.year == decision_year
        ).first()

        # Get outcome
        outcome = session.query(PostDecisionOutcome).filter(
            PostDecisionOutcome.course_id == course_id,
            PostDecisionOutcome.decision_year == decision_year,
            PostDecisionOutcome.outcome_year == outcome_year
        ).first()

        if not cd or not outcome:
            return {
                'course_id': course_id,
                'complete': False,
                'message': 'Karar veya outcome verisi bulunamadı',
            }

        # Get actual data from tables
        perf = session.query(Performans).filter(
            Performans.ders_id == course_id,
            Performans.akademik_yil == outcome_year
        ).first()

        pop = session.query(Populerlik).filter(
            Populerlik.ders_id == course_id,
            Populerlik.akademik_yil == outcome_year
        ).first()

        return {
            'course_id': course_id,
            'complete': True,
            'decision_year': decision_year,
            'outcome_year': outcome_year,
            'predicted_score': cd.topsis_score,
            'actual_performance': perf.ortalama_not if perf else None,
            'actual_success_rate': perf.basari_orani if perf else None,
            'actual_enrollment': pop.talep_sayisi if pop else None,
            'actual_capacity': pop.kontenjan if pop else None,
            'decision_was_effective': outcome.decision_was_effective,
        }
    finally:
        if close_session:
            session.close()


def generate_outcome_report(
    year: int,
    session: Optional[Session] = None,
) -> dict:
    """
    Bir karar yılı için outcome raporu.
    """
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        outcomes = session.query(PostDecisionOutcome).filter(
            PostDecisionOutcome.decision_year == year
        ).all()

        if not outcomes:
            return {
                'year': year,
                'total_outcomes': 0,
                'effective': 0,
                'stable': 0,
                'ineffective': 0,
                'unknown': 0,
                'average_fill_rate': 0.0,
                'average_success_rate': 0.0,
            }

        total = len(outcomes)
        effective = sum(1 for o in outcomes if o.decision_was_effective is True)
        ineffective = sum(1 for o in outcomes if o.decision_was_effective is False)
        unknown = sum(1 for o in outcomes if o.decision_was_effective is None)

        avg_fill_rate = sum(o.actual_fill_rate or 0 for o in outcomes) / total if total > 0 else 0
        avg_success_rate = sum(o.actual_success_rate or 0 for o in outcomes) / total if total > 0 else 0

        return {
            'year': year,
            'total_outcomes': total,
            'effective_count': effective,
            'ineffective_count': ineffective,
            'unknown_count': unknown,
            'effectiveness_ratio': round(float(effective) / float(total), 2) if total > 0 else 0,
            'average_fill_rate': round(float(avg_fill_rate or 0), 2),
            'average_success_rate': round(float(avg_success_rate or 0), 2),
        }
    finally:
        if close_session:
            session.close()
