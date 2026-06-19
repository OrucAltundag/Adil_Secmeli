from app.services.popularity_service import calculate_popularity_score


def test_full_formula_uses_capacity_attendance_and_absence():
    high = calculate_popularity_score(
        capacity=60,
        enrolled=50,
        attendance_count=14,
        total_weeks=14,
        attendance_percentage=100,
        absent_student_count=0,
    )
    low = calculate_popularity_score(
        capacity=60,
        enrolled=50,
        attendance_count=7,
        total_weeks=14,
        attendance_percentage=50,
        absent_student_count=25,
    )

    assert high["occupancy_ratio"] == low["occupancy_ratio"] == 0.833333
    assert high["popularity_score"] == 0.9
    assert low["popularity_score"] == 0.7


def test_missing_attendance_preserves_legacy_occupancy_score():
    result = calculate_popularity_score(capacity=60, enrolled=50)

    assert result["attendance_component"] is None
    assert result["popularity_score"] == result["occupancy_ratio"] == 0.833333
