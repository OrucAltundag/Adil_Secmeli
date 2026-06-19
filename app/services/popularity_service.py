from __future__ import annotations

from typing import Any


OCCUPANCY_WEIGHT = 0.60
ATTENDANCE_COUNT_WEIGHT = 0.15
ATTENDANCE_PERCENT_WEIGHT = 0.15
REGULARITY_WEIGHT = 0.10


def _number(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _ratio(value: Any) -> float | None:
    number = _number(value)
    if number is None:
        return None
    if number > 1.0:
        number /= 100.0
    return max(0.0, min(1.0, number))


def calculate_popularity_score(
    *,
    capacity: Any,
    enrolled: Any,
    attendance_count: Any = None,
    total_weeks: Any = None,
    attendance_percentage: Any = None,
    absent_student_count: Any = None,
) -> dict[str, float | None]:
    """Ders popülerliğini kapasite ve katılım sinyallerinden üretir.

    Tam veri olduğunda ağırlıklar:
      kapasite doluluğu %60,
      katılım sayısı / toplam hafta %15,
      bildirilen katılım yüzdesi %15,
      devamlılık (1 - devamsız öğrenci oranı) %10.

    Katılım alanları bulunmayan eski kayıtlarda mevcut davranış korunur ve
    skor yalnız kapasite doluluğuna eşit olur. Kısmi veride mevcut bileşenlerin
    ağırlıkları yeniden normalize edilir; eksik alan sıfır kabul edilmez.
    """
    capacity_value = _number(capacity) or 0.0
    enrolled_value = _number(enrolled) or 0.0
    occupancy = (
        max(0.0, min(1.0, enrolled_value / capacity_value))
        if capacity_value > 0
        else 0.0
    )

    attendance_count_value = _number(attendance_count)
    total_weeks_value = _number(total_weeks)
    attendance_from_count = None
    if attendance_count_value is not None and total_weeks_value is not None and total_weeks_value > 0:
        attendance_from_count = max(0.0, min(1.0, attendance_count_value / total_weeks_value))

    attendance_reported = _ratio(attendance_percentage)

    absent_value = _number(absent_student_count)
    regularity = None
    if absent_value is not None and enrolled_value > 0:
        regularity = 1.0 - max(0.0, min(1.0, absent_value / enrolled_value))

    components: list[tuple[float, float]] = [(occupancy, OCCUPANCY_WEIGHT)]
    if attendance_from_count is not None:
        components.append((attendance_from_count, ATTENDANCE_COUNT_WEIGHT))
    if attendance_reported is not None:
        components.append((attendance_reported, ATTENDANCE_PERCENT_WEIGHT))
    if regularity is not None:
        components.append((regularity, REGULARITY_WEIGHT))

    weight_total = sum(weight for _value, weight in components) or 1.0
    popularity = sum(value * weight for value, weight in components) / weight_total
    attendance_values = [
        value for value in (attendance_from_count, attendance_reported) if value is not None
    ]
    attendance_component = (
        sum(attendance_values) / len(attendance_values) if attendance_values else None
    )
    return {
        "occupancy_ratio": round(occupancy, 6),
        "attendance_count_ratio": (
            round(attendance_from_count, 6) if attendance_from_count is not None else None
        ),
        "attendance_percentage_ratio": (
            round(attendance_reported, 6) if attendance_reported is not None else None
        ),
        "attendance_component": (
            round(attendance_component, 6) if attendance_component is not None else None
        ),
        "regularity_ratio": round(regularity, 6) if regularity is not None else None,
        "popularity_score": round(max(0.0, min(1.0, popularity)), 6),
    }
