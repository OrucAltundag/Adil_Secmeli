# -*- coding: utf-8 -*-
"""
Faz 3 kapsamli test: H (MLP), F (Havuzdan Oner), G (Otomatik Karar).
Gercekci senaryo + kenar durum. PASS/FAIL raporu.
"""
import os
import shutil
import sqlite3
import sys
import tempfile
import traceback
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

SRC = os.path.join(os.path.dirname(__file__), "..", "data", "adil_secmeli.db")
TMP = os.path.join(tempfile.gettempdir(), "faz3_test.db")
shutil.copy2(SRC, TMP)

R = []


def T(ad, fn):
    try:
        ok, det = fn()
        R.append(("PASS" if ok else "FAIL", ad, det))
    except Exception as e:
        R.append(("FAIL", ad, f"{type(e).__name__}: {e}"))
        traceback.print_exc()


def _xy(n, seed=0):
    rng = np.random.RandomState(seed)
    X = pd.DataFrame(rng.rand(n, 4), columns=["a", "b", "c", "d"])
    y = ((X["a"] * 2 + X["b"] + 0.1 * rng.rand(n)) > 1.3).astype(int)
    return X, y


# ── H: MLP ───────────────────────────────────────────────────────────────────
def h_fit_predict():
    from app.algorithms.ml.classifiers import MLPPredictor
    X, y = _xy(200)
    m = MLPPredictor()
    m.fit(X, y)
    out = m.predict(X)
    pred = list(getattr(out, "predictions", out))
    acc = float((np.array(pred) == y.values).mean())
    return acc > 0.7, f"egitim acc={acc:.3f}"


def h_adaptif_katman():
    from app.services.ml_training_service import _build_model
    a = _build_model("mlp", 80).named_steps["mlp"].hidden_layer_sizes
    b = _build_model("deep_learning", 500).named_steps["mlp"].hidden_layer_sizes
    c = _build_model("neural_network", 5000).named_steps["mlp"].hidden_layer_sizes
    return (a == (32,) and b == (64, 32) and c == (128, 64, 32),
            f"80:{a} 500:{b} 5000:{c}")


def h_scaler_pipeline():
    from app.algorithms.ml.classifiers import _build_mlp_estimator
    est = _build_mlp_estimator()
    steps = [s[0] for s in est.steps]
    mlp = est.named_steps["mlp"]
    return ("scaler" in steps and mlp.early_stopping,
            f"steps={steps} early_stopping={mlp.early_stopping}")


def h_eval_significance():
    from app.services.ml_evaluation_service import evaluate_classification_model
    from app.services.ml_training_service import _build_model
    X, y = _xy(160)
    r = evaluate_classification_model(_build_model("mlp", 160), X, y)
    return (r.validation_metrics.get("accuracy", 0) > 0.6
            and r.significance.get("performed"),
            f"val acc={r.validation_metrics.get('accuracy',0):.2f} "
            f"sig={r.significance.get('significant')}")


def h_export():
    from app.algorithms.ml import MLPPredictor as A
    from app.algorithms.ml.classifiers import MLPPredictor as B
    return (A is B, "__init__ export OK")


# ── F: Havuzdan Oner ─────────────────────────────────────────────────────────
def f_temel():
    from app.services.pool_recommendation_service import recommend_from_pool
    conn = sqlite3.connect(TMP)
    r = recommend_from_pool(conn, year=2022, faculty_id=2, top_n=10,
                            oner_esigi=55)
    conn.close()
    on = r["oneriler"]
    sirali = all(on[i]["skor"] >= on[i + 1]["skor"] for i in range(len(on) - 1))
    return (len(on) > 0 and sirali
            and all(o["oneri"] in ("AC", "HAVUZDA_TUT") for o in on),
            f"{len(on)} oneri, skor-desc={sirali}, "
            f"top={on[0]['kod']}={on[0]['skor']}")


def f_agirlik_aktif_ahp():
    from app.services.pool_recommendation_service import recommend_from_pool
    conn = sqlite3.connect(TMP)
    r = recommend_from_pool(conn, year=2022, faculty_id=2)
    conn.close()
    s = sum(r["agirliklar"].values())
    return (abs(s - 1.0) < 1e-6 and set(r["agirliklar"]) >=
            {"basari", "trend", "populerlik", "anket"},
            f"agirlik toplam={s:.4f} keys={sorted(r['agirliklar'])}")


def f_esik_etkisi():
    from app.services.pool_recommendation_service import recommend_from_pool
    conn = sqlite3.connect(TMP)
    dusuk = recommend_from_pool(conn, year=2022, faculty_id=2, top_n=0,
                                oner_esigi=30)
    yuksek = recommend_from_pool(conn, year=2022, faculty_id=2, top_n=0,
                                 oner_esigi=90)
    conn.close()
    ac_d = sum(1 for o in dusuk["tum_siralama"] if o["oneri"] == "AC")
    ac_y = sum(1 for o in yuksek["tum_siralama"] if o["oneri"] == "AC")
    return (ac_d >= ac_y, f"esik30 AC={ac_d} >= esik90 AC={ac_y}")


def f_veri_yok_sayimi():
    from app.services.pool_recommendation_service import recommend_from_pool
    conn = sqlite3.connect(TMP)
    r = recommend_from_pool(conn, year=2022, faculty_id=2)
    conn.close()
    # kriter verisi olmayan dersler siralanmaz
    return (r["veri_yok"] >= 0 and r["toplam_aday"] >=
            len(r["tum_siralama"]),
            f"aday={r['toplam_aday']} siralanan={len(r['tum_siralama'])} "
            f"veri_yok={r['veri_yok']}")


def f_bos_fakulte():
    from app.services.pool_recommendation_service import recommend_from_pool
    conn = sqlite3.connect(TMP)
    r = recommend_from_pool(conn, year=2099, faculty_id=999)
    conn.close()
    return (r["toplam_aday"] == 0 and r["oneriler"] == [],
            "gecersiz yil/fakulte -> bos (crash yok)")


# ── G: Otomatik Karar Destek ─────────────────────────────────────────────────
def g_temel():
    from app.services.auto_decision_support_service import auto_decision_support
    conn = sqlite3.connect(TMP)
    r = auto_decision_support(conn, year=2022, faculty_id=2)
    conn.close()
    oz = r["ozet"]
    toplam_es = oz["ac"] + oz["havuzda_tut"] + oz["iptal_adayi"]
    return (toplam_es == oz["toplam"] and len(r["kararlar"]) == oz["toplam"],
            f"ac={oz['ac']} tut={oz['havuzda_tut']} iptal={oz['iptal_adayi']} "
            f"toplam={oz['toplam']}")


def g_karar_siralama():
    from app.services.auto_decision_support_service import auto_decision_support
    conn = sqlite3.connect(TMP)
    r = auto_decision_support(conn, year=2022, faculty_id=2)
    conn.close()
    k = r["kararlar"]
    sirali = all(k[i]["nihai_skor"] >= k[i + 1]["nihai_skor"]
                 for i in range(len(k) - 1))
    gecerli = all(x["karar"] in ("AC", "HAVUZDA_TUT", "IPTAL_ADAYI")
                  for x in k)
    return (sirali and gecerli, f"nihai-desc={sirali} kararlar gecerli={gecerli}")


def g_guven_araligi():
    from app.services.auto_decision_support_service import auto_decision_support
    conn = sqlite3.connect(TMP)
    r = auto_decision_support(conn, year=2022, faculty_id=2)
    conn.close()
    guvenler = [x["guven"] for x in r["kararlar"]]
    return (all(0.0 <= g <= 1.0 for g in guvenler),
            f"guven araligi [{min(guvenler):.2f},{max(guvenler):.2f}]"
            if guvenler else "kayit yok")


def g_gerekce_var():
    from app.services.auto_decision_support_service import auto_decision_support
    conn = sqlite3.connect(TMP)
    r = auto_decision_support(conn, year=2022, faculty_id=2)
    conn.close()
    return (all(len(x["gerekce"]) > 20 for x in r["kararlar"]),
            "her karar icin gerekce metni var")


def g_ml_kapali():
    from app.services.auto_decision_support_service import auto_decision_support
    conn = sqlite3.connect(TMP)
    r = auto_decision_support(conn, year=2022, faculty_id=2, use_ml=False)
    conn.close()
    return (not r["ozet"]["ml_kullanildi"]
            and all(x["ml_sinyal"] == 0.0 for x in r["kararlar"]),
            "use_ml=False -> ml_sinyal hep 0")


def g_bos_guvenli():
    from app.services.auto_decision_support_service import auto_decision_support
    conn = sqlite3.connect(TMP)
    r = auto_decision_support(conn, year=2099, faculty_id=999)
    conn.close()
    return (r["ozet"]["toplam"] == 0 and r["kararlar"] == [],
            "gecersiz girdi -> bos (crash yok)")


def main():
    T("H1 MLP fit+predict", h_fit_predict)
    T("H2 MLP adaptif katman boyutu", h_adaptif_katman)
    T("H3 MLP Scaler+earlystop pipeline", h_scaler_pipeline)
    T("H4 MLP eval + significance", h_eval_significance)
    T("H5 MLP __init__ export", h_export)
    T("F1 havuzdan oner temel + siralama", f_temel)
    T("F2 aktif AHP agirligi kullanilir", f_agirlik_aktif_ahp)
    T("F3 esik AC sayisini etkiler", f_esik_etkisi)
    T("F4 veri_yok sayimi tutarli", f_veri_yok_sayimi)
    T("F5 bos fakulte -> crash yok", f_bos_fakulte)
    T("G1 otomatik karar ozet tutarli", g_temel)
    T("G2 nihai_skor siralama + gecerli karar", g_karar_siralama)
    T("G3 guven 0-1 araliginda", g_guven_araligi)
    T("G4 her karar gerekceli", g_gerekce_var)
    T("G5 use_ml=False -> ml_sinyal 0", g_ml_kapali)
    T("G6 bos girdi -> crash yok", g_bos_guvenli)

    print("\n" + "=" * 64)
    print("FAZ 3 TEST RAPORU (H: MLP, F: Havuzdan Oner, G: Oto Karar)")
    print("=" * 64)
    p = sum(1 for x in R if x[0] == "PASS")
    f = sum(1 for x in R if x[0] == "FAIL")
    for d, ad, det in R:
        print(f"  [{'OK  ' if d == 'PASS' else 'FAIL'}] {ad:<40} {det}")
    print("-" * 64)
    print(f"TOPLAM: {p} PASS, {f} FAIL")
    return 0 if f == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
