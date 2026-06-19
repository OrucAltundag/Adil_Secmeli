# -*- coding: utf-8 -*-
"""
Faz 2 kapsamli test: C (p-value), D (pruning+adaptif), E (SHAP/LIME).
Gercekci senaryolar + kenar durumlar. PASS/FAIL raporu.
"""
import os
import sys
import traceback
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression

R = []


def T(ad, fn):
    try:
        ok, detay = fn()
        R.append(("PASS" if ok else "FAIL", ad, detay))
    except Exception as e:
        R.append(("FAIL", ad, f"{type(e).__name__}: {e}"))
        traceback.print_exc()


def veri(n, signal=True, seed=0):
    rng = np.random.RandomState(seed)
    X = pd.DataFrame(rng.rand(n, 4), columns=["basari", "trend", "populerlik", "anket"])
    if signal:
        y = ((X["basari"] * 2 + X["trend"] + 0.1 * rng.rand(n)) > 1.3).astype(int)
    else:
        y = pd.Series(rng.randint(0, 2, n))
    return X, y


# ─── C: p-value / significance ───────────────────────────────────────────────
def c_anlamli():
    from app.services.ml_evaluation_service import run_significance_test
    X, y = veri(150, signal=True)
    m = RandomForestClassifier(n_estimators=40, random_state=0)
    r = run_significance_test(m, X, y, task_type="classification", n_permutations=50)
    return (r.get("performed") and r.get("significant") and r["p_value"] < 0.05,
            f"p={r.get('p_value'):.4f} significant={r.get('significant')}")


def c_rastgele():
    from app.services.ml_evaluation_service import run_significance_test
    X, y = veri(150, signal=False)
    m = RandomForestClassifier(n_estimators=40, random_state=0)
    r = run_significance_test(m, X, y, task_type="classification", n_permutations=50)
    return (r.get("performed") and not r.get("significant"),
            f"p={r.get('p_value'):.4f} significant={r.get('significant')} (anlamsiz beklenir)")


def c_kucuk_veri():
    from app.services.ml_evaluation_service import run_significance_test
    X, y = veri(6, signal=True)
    r = run_significance_test(RandomForestClassifier(), X, y)
    return (not r.get("performed"), f"performed={r.get('performed')} (kucuk veri reddedilmeli)")


def c_tek_sinif():
    from app.services.ml_evaluation_service import run_significance_test
    X = pd.DataFrame(np.random.rand(30, 3))
    y = pd.Series([1] * 30)
    r = run_significance_test(RandomForestClassifier(), X, y)
    return (not r.get("performed"), f"performed={r.get('performed')} (tek sinif reddedilmeli)")


def c_regresyon():
    from app.services.ml_evaluation_service import run_significance_test
    rng = np.random.RandomState(1)
    X = pd.DataFrame(rng.rand(120, 3), columns=["a", "b", "c"])
    y = X["a"] * 5 + rng.rand(120) * 0.2
    r = run_significance_test(LinearRegression(), X, y, task_type="regression",
                              n_permutations=50)
    return (r.get("performed") and r.get("significant"),
            f"reg p={r.get('p_value'):.4f} significant={r.get('significant')}")


def c_entegrasyon():
    from app.services.ml_evaluation_service import (
        evaluate_classification_model, generate_evaluation_report)
    X, y = veri(120, signal=True)
    res = evaluate_classification_model(RandomForestClassifier(n_estimators=30,
                                        random_state=0), X, y)
    d = generate_evaluation_report(res)
    return ("significance" in d and d["significance"].get("performed"),
            f"as_dict significance var: {'significance' in d}")


# ─── D: pruning + adaptif ────────────────────────────────────────────────────
def d_adaptif_sinirlar():
    from app.services.ml_training_service import _adaptive_rf_params
    p50, p500, p5000 = (_adaptive_rf_params(50), _adaptive_rf_params(500),
                         _adaptive_rf_params(5000))
    ok = (p50["max_depth"] == 4 and p50["ccp_alpha"] == 0.01
          and p500["max_depth"] == 10
          and p5000["max_depth"] is None and p5000["ccp_alpha"] == 0.0)
    return ok, f"50:{p50['max_depth']} 500:{p500['max_depth']} 5000:{p5000['max_depth']}"


def d_build_model_pruning():
    from app.services.ml_training_service import _build_model
    rf = _build_model("random_forest", 50)
    dt = _build_model("decision_tree")
    rfp = rf.get_params()
    dtp = dt.get_params()
    ok = (rfp["ccp_alpha"] == 0.01 and rfp["max_depth"] == 4
          and dtp["ccp_alpha"] == 0.01 and dtp["min_samples_leaf"] == 4)
    return ok, f"RF ccp={rfp['ccp_alpha']} DT ccp={dtp['ccp_alpha']}"


def d_auto_key():
    from app.services.ml_training_service import _build_model
    a = _build_model("auto", 800)
    b = _build_model("adaptive", 800)
    return (a.get_params()["max_depth"] == 10 == b.get_params()["max_depth"],
            "auto/adaptive anahtarlari RF adaptif donuyor")


def d_build_adaptive_predictor():
    from app.algorithms.ml.classifiers import build_adaptive_predictor
    secimler = {}
    for n in (10, 80, 500, 5000):
        _, info = build_adaptive_predictor(n)
        secimler[n] = info["secim"]
    ok = ("Logistic" in secimler[10] and "guclu budama" in secimler[80]
          and "orta budama" in secimler[500] and "tam kapasite" in secimler[5000])
    return ok, str(secimler)


def d_adaptif_fit_predict():
    """Secilen model gercekten fit/predict edebiliyor mu."""
    from app.algorithms.ml.classifiers import build_adaptive_predictor
    X, y = veri(80, signal=True)
    model, _ = build_adaptive_predictor(80)
    model.fit(X, y)
    out = model.predict(X)
    pred = getattr(out, "predictions", out)
    pred_list = list(pred)  # type: ignore[arg-type]  # AlgorithmOutput runtime'da iterable
    return (pred is not None and len(pred_list) == len(X),
            f"fit+predict OK, {len(pred_list)} tahmin")


def d_pruning_overfit_azaltir():
    """Budanmis agac, budanmamisa gore train-val gap'i dusuk olmali."""
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.model_selection import train_test_split
    X, y = veri(200, signal=True, seed=3)
    Xtr, Xv, ytr, yv = train_test_split(X, y, test_size=0.3, random_state=1)
    budanmamis = DecisionTreeClassifier(random_state=1).fit(Xtr, ytr)
    budanmis = DecisionTreeClassifier(max_depth=4, min_samples_leaf=5,
                                      ccp_alpha=0.01, random_state=1).fit(Xtr, ytr)
    g0 = budanmamis.score(Xtr, ytr) - budanmamis.score(Xv, yv)
    g1 = budanmis.score(Xtr, ytr) - budanmis.score(Xv, yv)
    return (g1 <= g0 + 0.02, f"gap budanmamis={g0:.3f} budanmis={g1:.3f}")


# ─── E: SHAP / LIME ──────────────────────────────────────────────────────────
def e_shap_tree():
    from app.services.ml_explainability_service import get_shap_explanation
    X, y = veri(150, signal=True)
    m = RandomForestClassifier(n_estimators=40, random_state=0).fit(X, y)
    r = get_shap_explanation(m, X.iloc[[0]], list(X.columns))
    ok = r and "top" in r and len(r["top"]) > 0 and "error" not in r
    return ok, f"top={[t['feature'] for t in r.get('top',[])]}" if r else "None"


def e_shap_nontree():
    from app.services.ml_explainability_service import get_shap_explanation
    X, y = veri(120, signal=True)
    m = LogisticRegression(max_iter=500).fit(X, y)
    r = get_shap_explanation(m, X.iloc[[0]], list(X.columns), background=X)
    return (r and "top" in r and "error" not in r,
            "non-tree SHAP ok" if r and "top" in r else str(r))


def e_lime_clf():
    from app.services.ml_explainability_service import get_lime_explanation
    X, y = veri(150, signal=True)
    m = RandomForestClassifier(n_estimators=40, random_state=0).fit(X, y)
    r = get_lime_explanation(m, X.iloc[[0]], list(X.columns), X)
    ok = r and "explanation" in r and len(r["explanation"]) > 0
    return ok, f"{len(r.get('explanation',[]))} kural" if r else "None"


def e_lime_no_training():
    from app.services.ml_explainability_service import get_lime_explanation
    X, y = veri(50, signal=True)
    m = RandomForestClassifier(n_estimators=20, random_state=0).fit(X, y)
    r = get_lime_explanation(m, X.iloc[[0]], list(X.columns), None)
    return (r is None, "training_data=None -> None (beklenen)")


def e_real_estimator_raw_rf():
    """KRITIK: ham sklearn RF'nin .estimator'u unfitted; dogru secilmeli."""
    from app.services.ml_explainability_service import _real_estimator
    X, y = veri(60, signal=True)
    m = RandomForestClassifier(n_estimators=20, random_state=0).fit(X, y)
    est = _real_estimator(m)
    return (hasattr(est, "estimators_"),
            "fitted RF secildi" if hasattr(est, "estimators_") else "YANLIS: unfitted")


def e_real_estimator_wrapper():
    from app.services.ml_explainability_service import _real_estimator
    from app.algorithms.ml.classifiers import RandomForestPredictor
    X, y = veri(60, signal=True)
    w = RandomForestPredictor(n_estimators=20)
    w.fit(X, y)
    est = _real_estimator(w)
    return (hasattr(est, "estimators_") or hasattr(est, "feature_importances_"),
            "wrapper'dan fitted estimator cikti")


def e_entegrasyon():
    from app.services.ml_explainability_service import explain_model_prediction
    X, y = veri(150, signal=True)
    m = RandomForestClassifier(n_estimators=30, random_state=0).fit(X, y)
    exp = explain_model_prediction(m, X.iloc[[0]], list(X.columns),
                                   "random_forest", training_data=X)
    d = exp.as_dict()
    ok = (d.get("shap_json") and d.get("lime_json")
          and "shap_json" in d and "lime_json" in d)
    return ok, f"shap={bool(d.get('shap_json'))} lime={bool(d.get('lime_json'))}"


def e_shap_dogruluk():
    """SHAP en onemli feature, gercek sinyal feature'i ile ortusmeli."""
    from app.services.ml_explainability_service import get_shap_explanation
    rng = np.random.RandomState(7)
    X = pd.DataFrame(rng.rand(200, 4), columns=["basari", "trend", "populerlik", "anket"])
    y = (X["basari"] > 0.5).astype(int)  # sadece basari belirleyici
    m = RandomForestClassifier(n_estimators=60, random_state=0).fit(X, y)
    r = get_shap_explanation(m, X.iloc[[0]], list(X.columns))
    en_onemli = r["top"][0]["feature"] if r and r.get("top") else None
    return (en_onemli == "basari",
            f"en onemli SHAP feature='{en_onemli}' (beklenen 'basari')")


def main():
    # C
    T("C1 anlamli veri -> significant", c_anlamli)
    T("C2 rastgele veri -> not significant", c_rastgele)
    T("C3 kucuk veri reddi (<10)", c_kucuk_veri)
    T("C4 tek sinif reddi", c_tek_sinif)
    T("C5 regresyon significance", c_regresyon)
    T("C6 evaluate_*'a entegrasyon (as_dict)", c_entegrasyon)
    # D
    T("D1 adaptif RF param sinirlari", d_adaptif_sinirlar)
    T("D2 _build_model pruning (RF+DT)", d_build_model_pruning)
    T("D3 auto/adaptive algorithm_key", d_auto_key)
    T("D4 build_adaptive_predictor esikleri", d_build_adaptive_predictor)
    T("D5 adaptif model fit+predict", d_adaptif_fit_predict)
    T("D6 pruning overfit-gap azaltir", d_pruning_overfit_azaltir)
    # E
    T("E1 SHAP agac modeli", e_shap_tree)
    T("E2 SHAP agac-disi (LogReg)", e_shap_nontree)
    T("E3 LIME siniflandirma", e_lime_clf)
    T("E4 LIME training_data yok -> None", e_lime_no_training)
    T("E5 _real_estimator ham RF (kritik)", e_real_estimator_raw_rf)
    T("E6 _real_estimator wrapper", e_real_estimator_wrapper)
    T("E7 explain_model_prediction entegrasyon", e_entegrasyon)
    T("E8 SHAP dogruluk (sinyal feature)", e_shap_dogruluk)

    print("\n" + "=" * 66)
    print("FAZ 2 TEST RAPORU (C: p-value, D: pruning/adaptif, E: SHAP/LIME)")
    print("=" * 66)
    p = sum(1 for x in R if x[0] == "PASS")
    f = sum(1 for x in R if x[0] == "FAIL")
    for d, ad, det in R:
        print(f"  [{'OK  ' if d == 'PASS' else 'FAIL'}] {ad:<42} {det}")
    print("-" * 66)
    print(f"TOPLAM: {p} PASS, {f} FAIL")
    return 0 if f == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
