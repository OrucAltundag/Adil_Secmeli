# -*- coding: utf-8 -*-
"""
Data Collection Priority Service

Veri toplama için öncelikler belirler ve önerir.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import (
    Bolum,
    DataCollectionPriority,
    Ders,
    Fakülte,
    MissingDataItem,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _json_dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def generate_collection_priorities(
    year: int,
    faculty_id: Optional[int] = None,
    department_id: Optional[int] = None,
    session: Optional[Session] = None,
) -> list[DataCollectionPriority]:
    """
    Veri toplama öncelikleri üret.

    Öncelliklendirme mantığı:
    1. Düşük güven kararları (critical missing data)
    2. Sınırdaki kararlar (score boundary near)
    3. Yüksek etkili dersler
    4. Fakülte/bölüm coverage düşükse tüm bölüm
    """
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        priorities = []
        rank = 1

        # Get all missing data items
        q = session.query(MissingDataItem).filter(
            MissingDataItem.year == year,
            MissingDataItem.resolved_at.is_(None)
        )

        if faculty_id:
            q = q.filter(MissingDataItem.faculty_id == faculty_id)
        if department_id:
            q = q.filter(MissingDataItem.department_id == department_id)

        missing_items = q.all()

        # Group by course and calculate impact
        by_course = {}
        for item in missing_items:
            course_id = item.course_id
            if course_id not in by_course:
                by_course[course_id] = {
                    'critical_count': 0,
                    'warning_count': 0,
                    'missing_fields': set(),
                    'faculty_id': item.faculty_id,
                    'department_id': item.department_id,
                }

            by_course[course_id]['missing_fields'].add(item.missing_field)

            if item.severity == 'critical':
                by_course[course_id]['critical_count'] += 1
            elif item.severity == 'warning':
                by_course[course_id]['warning_count'] += 1

        # Sort by criticality
        sorted_courses = sorted(
            by_course.items(),
            key=lambda x: (x[1]['critical_count'], x[1]['warning_count']),
            reverse=True
        )

        # Create priorities
        for course_id, data in sorted_courses:
            course = session.query(Ders).filter(Ders.ders_id == course_id).first()
            if not course:
                continue

            # Determine impact based on missing data severity
            if data['critical_count'] >= 2:
                impact = "high"
                reason = f"Kritik veriler eksik ({data['critical_count']} alan)"
            elif data['critical_count'] == 1:
                impact = "medium"
                reason = "En az 1 kritik veri eksik"
            else:
                impact = "low"
                reason = f"İkincil veriler eksik ({len(data['missing_fields'])} alan)"

            # Build suggested action
            field_list = ', '.join(sorted(data['missing_fields']))
            action = f"{course.ad} için {field_list} verisi toplanmalı."

            priority = DataCollectionPriority(
                scope_type="course",
                faculty_id=data['faculty_id'],
                department_id=data['department_id'],
                year=year,
                priority_rank=rank,
                target_entity_type="course",
                course_id=course_id,
                missing_field=field_list,
                priority_reason=reason,
                expected_impact=impact,
                suggested_action=action,
                status="open",
                created_at=_now(),
            )
            session.add(priority)
            priorities.append(priority)
            rank += 1

        session.commit()

        # Check for department-level priorities (if coverage is very low)
        if not faculty_id and not department_id:
            faculties = session.query(Fakülte).all()
            for fak in faculties:
                dept_count = session.query(Bolum).filter(Bolum.fakulte_id == fak.fakulte_id).count()
                for dept in session.query(Bolum).filter(Bolum.fakulte_id == fak.fakulte_id):
                    low_priority = session.query(DataCollectionPriority).filter(
                        DataCollectionPriority.faculty_id == fak.fakulte_id,
                        DataCollectionPriority.department_id == dept.bolum_id,
                        DataCollectionPriority.year == year
                    ).count()

                    if low_priority > (session.query(Ders).filter(Ders.bolum_id == dept.bolum_id).count() / 2):
                        priority = DataCollectionPriority(
                            scope_type="department",
                            faculty_id=fak.fakulte_id,
                            department_id=dept.bolum_id,
                            year=year,
                            priority_rank=rank,
                            target_entity_type="department",
                            priority_reason=f"{dept.ad} bölümü için veri doluluğu çok düşük",
                            expected_impact="high",
                            suggested_action="Bölüm başkanı ile iletişim: Tüm dersler için veri toplanmalı.",
                            status="open",
                            created_at=_now(),
                        )
                        session.add(priority)
                        priorities.append(priority)
                        rank += 1

        session.commit()

        return priorities
    finally:
        if close_session:
            session.close()


def mark_priority_completed(
    priority_id: int,
    session: Optional[Session] = None,
) -> Optional[DataCollectionPriority]:
    """
    Veri toplama görevini tamamlandı olarak işaretle.
    """
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        priority = session.query(DataCollectionPriority).filter(
            DataCollectionPriority.id == priority_id
        ).first()

        if priority:
            priority.status = "completed"
            priority.completed_at = _now()
            session.commit()

        return priority
    finally:
        if close_session:
            session.close()


def get_open_priorities(
    year: int,
    faculty_id: Optional[int] = None,
    session: Optional[Session] = None,
) -> list[dict]:
    """
    Açık (yapılmamış) veri toplama öncelikleri.
    """
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        q = session.query(DataCollectionPriority).filter(
            DataCollectionPriority.year == year,
            DataCollectionPriority.status == "open"
        )

        if faculty_id:
            q = q.filter(DataCollectionPriority.faculty_id == faculty_id)

        priorities = q.order_by(DataCollectionPriority.priority_rank).all()

        results = []
        for p in priorities:
            results.append({
                'id': p.id,
                'priority_rank': p.priority_rank,
                'target_type': p.target_entity_type,
                'course_id': p.course_id,
                'course_name': session.query(Ders).filter(Ders.ders_id == p.course_id).first().ad if p.course_id else None,
                'missing_field': p.missing_field,
                'reason': p.priority_reason,
                'expected_impact': p.expected_impact,
                'action': p.suggested_action,
                'status': p.status,
            })

        return results
    finally:
        if close_session:
            session.close()
