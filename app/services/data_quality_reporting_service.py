# -*- coding: utf-8 -*-
"""
Data Quality Reporting Service

Kapsamlı veri kalitesi ve hazırlık raporları.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import (
    DataCollectionPriority,
    DataValidationIssue,
    Ders,
    LowConfidenceDecisionFlag,
    MissingDataItem,
)
from app.services.data_coverage_service import calculate_coverage_ratios
from app.services.data_readiness_service import calculate_readiness_score


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _json_dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def generate_data_quality_dashboard(
    year: int,
    faculty_id: Optional[int] = None,
    session: Optional[Session] = None,
) -> dict:
    """
    Kapsamlı veri kalitesi dashboard'u.
    """
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        # Get all metrics
        coverage = calculate_coverage_ratios(session, year, faculty_id)
        readiness = calculate_readiness_score(session, year, faculty_id)

        # Count issues
        q = session.query(DataValidationIssue).filter(
            DataValidationIssue.year == year,
            DataValidationIssue.is_resolved.is_(False)
        )
        if faculty_id:
            q = q.filter(DataValidationIssue.faculty_id == faculty_id)

        validation_issues = q.count()
        critical_issues = q.filter(DataValidationIssue.severity == "critical").count()

        # Count missing data
        q = session.query(MissingDataItem).filter(
            MissingDataItem.year == year,
            MissingDataItem.resolved_at.is_(None)
        )
        if faculty_id:
            q = q.filter(MissingDataItem.faculty_id == faculty_id)

        missing_data_count = q.count()
        critical_missing = q.filter(MissingDataItem.severity == "critical").count()

        # Count low confidence decisions
        q = session.query(LowConfidenceDecisionFlag).filter(
            LowConfidenceDecisionFlag.year == year
        )
        if faculty_id:
            q = q.filter(LowConfidenceDecisionFlag.confidence_level.in_(["low", "medium"]))

        low_confidence_decisions = q.count()

        # Count collection priorities
        q = session.query(DataCollectionPriority).filter(
            DataCollectionPriority.year == year,
            DataCollectionPriority.status == "open"
        )
        if faculty_id:
            q = q.filter(DataCollectionPriority.faculty_id == faculty_id)

        collection_priorities = q.count()
        high_impact = q.filter(DataCollectionPriority.expected_impact == "high").count()

        return {
            'year': year,
            'faculty_id': faculty_id,
            'summary': {
                'total_courses': coverage['total_courses'],
                'courses_with_data': coverage['total_courses'] - (coverage['total_courses'] - coverage['courses_with_criteria']),
                'data_coverage_score': coverage['overall_score'],
                'data_readiness_score': readiness['readiness_score'],
                'readiness_level': readiness['readiness_level'],
            },
            'quality_metrics': {
                'validation_issues': validation_issues,
                'critical_validation_issues': critical_issues,
                'missing_data_items': missing_data_count,
                'critical_missing_data': critical_missing,
                'low_confidence_decisions': low_confidence_decisions,
                'collection_priorities_open': collection_priorities,
                'high_impact_priorities': high_impact,
            },
            'coverage': coverage,
            'readiness': readiness,
        }
    finally:
        if close_session:
            session.close()


def generate_missing_data_report(
    year: int,
    faculty_id: Optional[int] = None,
    session: Optional[Session] = None,
) -> dict:
    """
    Eksik veri raporu.
    """
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        q = session.query(MissingDataItem).filter(
            MissingDataItem.year == year,
            MissingDataItem.resolved_at.is_(None)
        )

        if faculty_id:
            q = q.filter(MissingDataItem.faculty_id == faculty_id)

        items = q.all()

        # Group by field
        by_field = {}
        for item in items:
            field = item.missing_field
            if field not in by_field:
                by_field[field] = {'critical': 0, 'warning': 0, 'info': 0, 'total': 0}

            by_field[field]['total'] += 1
            if item.severity == 'critical':
                by_field[field]['critical'] += 1
            elif item.severity == 'warning':
                by_field[field]['warning'] += 1
            else:
                by_field[field]['info'] += 1

        return {
            'year': year,
            'total_missing_items': len(items),
            'critical_items': sum(1 for i in items if i.severity == 'critical'),
            'warning_items': sum(1 for i in items if i.severity == 'warning'),
            'by_field': by_field,
            'items': [
                {
                    'course_id': i.course_id,
                    'course_name': session.query(Ders).filter(Ders.ders_id == i.course_id).first().ad if i.course_id else None,
                    'missing_field': i.missing_field,
                    'severity': i.severity,
                    'message': i.message,
                }
                for i in items
            ]
        }
    finally:
        if close_session:
            session.close()


def generate_validation_issues_report(
    year: int,
    faculty_id: Optional[int] = None,
    session: Optional[Session] = None,
) -> dict:
    """
    Data validation issues raporu.
    """
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        q = session.query(DataValidationIssue).filter(
            DataValidationIssue.year == year,
            DataValidationIssue.is_resolved.is_(False)
        )

        if faculty_id:
            q = q.filter(DataValidationIssue.faculty_id == faculty_id)

        issues = q.all()

        # Group by type and source
        by_type = {}
        by_source = {}

        for issue in issues:
            # By type
            t = issue.issue_type
            if t not in by_type:
                by_type[t] = 0
            by_type[t] += 1

            # By source
            s = issue.source_type
            if s not in by_source:
                by_source[s] = 0
            by_source[s] += 1

        return {
            'year': year,
            'total_issues': len(issues),
            'critical': sum(1 for i in issues if i.severity == 'critical'),
            'error': sum(1 for i in issues if i.severity == 'error'),
            'warning': sum(1 for i in issues if i.severity == 'warning'),
            'info': sum(1 for i in issues if i.severity == 'info'),
            'by_issue_type': by_type,
            'by_source_type': by_source,
            'open_issues': [
                {
                    'issue_type': i.issue_type,
                    'severity': i.severity,
                    'source_type': i.source_type,
                    'field_name': i.field_name,
                    'message': i.message,
                    'suggested_action': i.suggested_action,
                }
                for i in issues
            ]
        }
    finally:
        if close_session:
            session.close()


def generate_readiness_report(
    year: int,
    faculty_id: Optional[int] = None,
    session: Optional[Session] = None,
) -> dict:
    """
    Data readiness değerlendirme raporu.
    """
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        readiness = calculate_readiness_score(session, year, faculty_id)

        # Generate recommendations
        recommendations = []
        if readiness['readiness_level'] in ['not_ready', 'low']:
            recommendations.append("⚠️ Veri olgunluğu düşük. Kararlar ön değerlendirme olarak kullanılmalıdır.")

            if readiness['criteria_score'] < 40:
                recommendations.append("📊 Kriter verisi toplanmalı (hedef: %40+)")
            if readiness['performance_score'] < 40:
                recommendations.append("📈 Performans verisi toplanmalı (hedef: %40+)")
            if readiness['survey_score'] < 40:
                recommendations.append("📋 Anket verisi toplanmalı (hedef: %40+)")

        if readiness['blocking_issues'] > 0:
            recommendations.append(f"🚫 {readiness['blocking_issues']} kritik validation issue çözülmeli.")

        return {
            'year': year,
            'readiness_score': readiness['readiness_score'],
            'readiness_level': readiness['readiness_level'],
            'component_scores': {
                'criteria': readiness['criteria_score'],
                'performance': readiness['performance_score'],
                'popularity': readiness['popularity_score'],
                'survey': readiness['survey_score'],
                'trend': readiness['trend_score'],
                'validation': readiness['validation_score'],
            },
            'issues': {
                'blocking': readiness['blocking_issues'],
                'warning': readiness['warning_issues'],
            },
            'recommendations': recommendations,
            'can_make_decisions': readiness['readiness_level'] in ['good', 'decision_ready'],
        }
    finally:
        if close_session:
            session.close()
