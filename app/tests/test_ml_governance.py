import os
import sqlite3
import tempfile

import pandas as pd
from sklearn.tree import DecisionTreeClassifier

from app.api import routes
from app.benchmark.registry import AlgorithmRegistry
from app.db.schema_compat import ensure_ml_governance_schema
from app.services.ml_algorithm_registry_service import get_algorithm_config, seed_default_algorithm_registry
from app.services.ml_confidence_service import combine_confidence_signals, confidence_from_sample_size
from app.services.ml_evaluation_service import detect_overfitting, run_cross_validation
from app.services.ml_explainability_service import explain_model_prediction
from app.services.ml_feature_pipeline import build_course_feature_dataset
from app.services.ml_model_registry_service import list_model_runs
from app.services.ml_prediction_service import predict_course
from app.services.ml_readiness_service import check_model_readiness
from app.services.ml_training_service import train_model_run


def _temp_db(rows: int = 24) -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE okul (school_id INTEGER PRIMARY KEY, ad TEXT, kampus TEXT);
        CREATE TABLE fakulte (fakulte_id INTEGER PRIMARY KEY, ad TEXT, okul_id INTEGER, tip TEXT, kampus TEXT);
        CREATE TABLE bolum (bolum_id INTEGER PRIMARY KEY, fakulte_id INTEGER, ad TEXT);
        CREATE TABLE ders (
            ders_id INTEGER PRIMARY KEY,
            kod TEXT,
            ad TEXT,
            fakulte_id INTEGER,
            bolum_id INTEGER,
            DersTipi TEXT,
            tip TEXT,
            kredi INTEGER,
            akts INTEGER,
            kontenjan INTEGER
        );
        CREATE TABLE havuz (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id TEXT,
            fakulte_id INTEGER,
            bolum_id INTEGER,
            yil INTEGER,
            donem TEXT,
            statu INTEGER,
            sayac INTEGER,
            skor REAL
        );
        CREATE TABLE ders_kriterleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER,
            yil INTEGER,
            donem TEXT,
            toplam_ogrenci INTEGER,
            gecen_ogrenci INTEGER,
            basari_ortalamasi REAL,
            kontenjan INTEGER,
            kayitli_ogrenci INTEGER,
            anket_katilimci INTEGER,
            anket_dersi_secen INTEGER
        );
        CREATE TABLE performans (
            pfrs_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER,
            akademik_yil INTEGER,
            donem TEXT,
            ortalama_not REAL,
            basari_orani REAL
        );
        CREATE TABLE populerlik (
            pop_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER,
            akademik_yil INTEGER,
            donem TEXT,
            talep_sayisi INTEGER,
            kontenjan INTEGER,
            doluluk_orani REAL,
            ham_puan REAL
        );
        CREATE TABLE skor (
            skor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER,
            akademik_yil INTEGER,
            donem TEXT,
            b_norm REAL,
            p_norm REAL,
            a_norm REAL,
            g_norm REAL,
            skor_top REAL,
            hesap_tarih TEXT
        );
        """
    )
    cur.execute("INSERT INTO okul VALUES (1, 'Okul', 'Merkez')")
    cur.execute("INSERT INTO fakulte VALUES (1, 'M├╝hendislik', 1, 'Fak├╝lte', 'Merkez')")
    cur.execute("INSERT INTO bolum VALUES (10, 1, 'Bilgisayar')")
    for idx in range(rows):
        ders_id = 1000 + idx
        capacity = 0 if idx == 0 else 50 + (idx % 5)
        enrolled = 30 + (idx % 10)
        total = 40 + (idx % 12)
        passed = max(0, total - (idx % 8))
        status = 1 if idx % 2 == 0 else 0
        cur.execute("INSERT INTO ders VALUES (?, ?, ?, 1, 10, 'Se├ğmeli', 'Se├ğmeli', 3, 5, ?)", (ders_id, f"BLM{idx}", f"Ders {idx}", capacity))
        cur.execute("INSERT INTO havuz (ders_id, fakulte_id, bolum_id, yil, donem, statu, sayac, skor) VALUES (?, 1, 10, 2026, 'Guz', ?, ?, ?)", (str(ders_id), status, idx % 3, 40 + idx))
        cur.execute("INSERT INTO ders_kriterleri VALUES (NULL, ?, 2026, 'Guz', ?, ?, ?, ?, ?, ?, ?)", (ders_id, total, passed, 55 + idx % 40, capacity, enrolled, 20 + idx, 5 + idx))
        cur.execute("INSERT INTO performans VALUES (NULL, ?, 2026, 'Guz', ?, ?)", (ders_id, 55 + idx % 40, passed / total))
        cur.execute("INSERT INTO populerlik VALUES (NULL, ?, 2026, 'Guz', ?, ?, ?, ?)", (ders_id, enrolled, capacity, enrolled / capacity if capacity else 0.0, enrolled / max(capacity, 1)))
        cur.execute("INSERT INTO skor VALUES (NULL, ?, 2026, 'Guz', 0.5, 0.5, 0.5, 0.5, ?, NULL)", (ders_id, 35 + idx))
    conn.commit()
    conn.close()
    return path


def _conn(path: str):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    ensure_ml_governance_schema(conn)
    return conn


def test_algorithm_registry_defaults_and_roles():
    path = _temp_db()
    try:
        conn = _conn(path)
        seed_default_algorithm_registry(conn)
        rf = get_algorithm_config(conn, "random_forest")
        xgb = get_algorithm_config(conn, "xgboost")
        assert rf.min_training_samples == 200
        assert rf.usage_role == "advisory_ml"
        assert xgb.usage_role == "benchmark_only"
    finally:
        conn.close()
        os.unlink(path)


def test_readiness_blocks_small_random_forest_and_warns_imbalance():
    path = _temp_db()
    try:
        conn = _conn(path)
        df = pd.DataFrame({"x": range(24), "target_status": [1] * 22 + [0] * 2})
        readiness = check_model_readiness(conn, "random_forest", df, target_column="target_status")
        assert readiness.can_use_for_production_decision is False
        assert readiness.readiness_level in {"not_ready", "low"}
        assert readiness.required_min_samples == 200
        assert any("dengesiz" in warning for warning in readiness.warnings)
    finally:
        conn.close()
        os.unlink(path)


def test_readiness_high_when_sample_count_is_sufficient_but_advisory_not_production():
    path = _temp_db()
    try:
        conn = _conn(path)
        df = pd.DataFrame({"x": range(220), "target_status": [0, 1] * 110})
        readiness = check_model_readiness(conn, "random_forest", df, target_column="target_status")
        assert readiness.readiness_level in {"high", "medium"}
        assert readiness.can_use_for_advisory is True
        assert readiness.can_use_for_production_decision is False
    finally:
        conn.close()
        os.unlink(path)


def test_feature_pipeline_normalizes_and_handles_zero_capacity():
    path = _temp_db()
    try:
        conn = _conn(path)
        dataset = build_course_feature_dataset(conn, year=2026, faculty_id=1)
        assert dataset.feature_schema_version == "course_features_v1"
        assert dataset.sample_count == 24
        assert "success_rate" in dataset.feature_names
        assert dataset.X["success_rate"].between(0, 1).all()
        assert dataset.X.iloc[0]["enrollment_rate"] == 0.0
        assert dataset.missing_features_summary
    finally:
        conn.close()
        os.unlink(path)


def test_model_run_skipped_when_data_insufficient_and_trained_when_sufficient():
    path_small = _temp_db(rows=24)
    path_big = _temp_db(rows=120)
    try:
        conn = _conn(path_small)
        skipped = train_model_run(conn, algorithm_key="random_forest", year=2026, faculty_id=1)
        assert skipped["status"] == "skipped"
        assert skipped["skip_reason"]
        conn.close()

        conn = _conn(path_big)
        trained = train_model_run(conn, algorithm_key="decision_tree", year=2026, faculty_id=1)
        assert trained["status"] in {"trained", "failed"}
        if trained["status"] == "trained":
            assert trained["train_metrics"]
            assert trained["validation_metrics"] is not None
        assert list_model_runs(conn)
    finally:
        try:
            conn.close()
        except Exception:
            pass
        os.unlink(path_small)
        os.unlink(path_big)


def test_evaluation_overfit_and_small_cv_warning():
    report = detect_overfitting({"accuracy": 0.98}, {"accuracy": 0.54}, metric_name="accuracy")
    assert report["overfit_warning"] is True
    cv = run_cross_validation(DecisionTreeClassifier(), pd.DataFrame({"x": [1, 2, 3]}), pd.Series([0, 1, 0]))
    assert cv["performed"] is False


def test_confidence_low_with_low_sample_and_never_influences():
    signal = confidence_from_sample_size(24, 200)
    confidence = combine_confidence_signals([signal], readiness_level="not_ready")
    assert confidence.confidence_level == "low"
    assert confidence.should_influence_decision is False


def test_prediction_fallback_is_logged_and_advisory_only():
    path = _temp_db(rows=24)
    try:
        conn = _conn(path)
        prediction = predict_course(conn, algorithm_key="random_forest", course_id=1000, year=2026, faculty_id=1)
        assert prediction["fallback_used"] is True
        assert prediction["fallback_reason"]
        assert prediction["advisory_only"] is True
        assert prediction["should_influence_decision"] is False
        assert "nihai karara etki etmez" in prediction["explanation"]
    finally:
        conn.close()
        os.unlink(path)


def test_explainability_tree_path_and_low_data_limitation():
    X = pd.DataFrame({"success_rate": [0.2, 0.9, 0.4, 0.8], "enrollment_rate": [0.1, 0.8, 0.2, 0.7]})
    y = pd.Series([0, 1, 0, 1])
    model = DecisionTreeClassifier(max_depth=2, random_state=42).fit(X, y)
    explanation = explain_model_prediction(model, X.iloc[[0]], X.columns.tolist(), "decision_tree", readiness_level="low", sample_count=4)
    assert explanation.decision_path_json
    assert explanation.limitations
    assert "nihai karar de─şildir" in explanation.human_readable_text


def test_benchmark_registry_marks_ml_roles():
    algorithms = AlgorithmRegistry().list_algorithms()
    rf = next(item for item in algorithms if item["name"] == "RandomForest")
    xgb = next(item for item in algorithms if item["name"] == "XGBoostLike")
    assert rf["usage_role"] == "advisory_ml"
    assert xgb["usage_role"] == "benchmark_only"


def test_ml_api_smoke(monkeypatch):
    path = _temp_db(rows=24)
    monkeypatch.setattr(routes, "_get_db_path", lambda: path)
    try:
        algorithms = routes.ml_algorithms()
        readiness = routes.ml_readiness(year=2026, faculty_id=1)
        runs = routes.ml_model_runs()
        assert algorithms["success"] is True
        assert readiness["success"] is True
        assert runs["success"] is True
    finally:
        os.unlink(path)


def test_ml_readiness_page_importable():
    from app.ui.benchmark.pages.ml_readiness_page import MLReadinessPage

    assert MLReadinessPage is not None
