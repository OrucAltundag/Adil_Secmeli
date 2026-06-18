import sqlite3

from app.services.trend_analysis_service import analyze_course_finalized_score_trend


def _db():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE skor (ders_id INTEGER, akademik_yil INTEGER, skor_top REAL)")
    conn.execute("CREATE TABLE havuz (ders_id INTEGER, yil INTEGER, skor REAL)")
    return conn


def test_source_year_score_is_never_used_as_its_own_trend():
    conn = _db()
    conn.execute("INSERT INTO skor VALUES (1, 2022, 80)")
    result = analyze_course_finalized_score_trend(conn.cursor(), 1, 2022)
    assert result["trend_score"] == 0.5
    assert result["data_points_count"] == 0


def test_next_run_can_use_one_prior_finalized_score():
    conn = _db()
    conn.execute("INSERT INTO skor VALUES (1, 2022, 80)")
    conn.execute("INSERT INTO skor VALUES (1, 2023, 20)")
    result = analyze_course_finalized_score_trend(conn.cursor(), 1, 2023)
    assert result["values_by_year"] == {2022: 0.8}
    assert result["trend_score"] == 0.8
    assert result["trend_label"] == "single_finalized_score"
