# app/tests/test_single_analysis.py
"""
Birim + entegrasyon-lite testleri.

Calistir:
    python -m pytest app/tests/test_single_analysis.py -v
veya:
    python app/tests/test_single_analysis.py
"""

import sys
import os
import sqlite3
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.havuz_karar import (
    calculate_next_status,
    STATU_MUFREDATTA, STATU_HAVUZDA, STATU_DINLENMEDE, STATU_IPTAL,
    MAKS_DUSME_SAYACI,
)
from app.services.course_analyzer import (
    analyze_single_course,
    VeriEksikHatasi,
    _run_ahp,
    _run_topsis_single,
    _run_trend,
    _run_rf_simple,
)


# ===========================================================================
# KISIM 1: State Machine birim testleri (calculate_next_status)
# ===========================================================================

def test_sm_kalici_iptal_degismez():
    """S1: -2 her kosulda -2 kalir."""
    assert calculate_next_status(-2, 2, True)  == (-2, 2)
    assert calculate_next_status(-2, 2, False) == (-2, 2)
    assert calculate_next_status(-2, 0, True)  == (-2, 0)


def test_sm_dinlenmede_havuza_donus():
    """S2: -1 her kosulda 0 olur (in_mufredat True olsa bile)."""
    assert calculate_next_status(-1, 1, True)  == (0, 1)
    assert calculate_next_status(-1, 1, False) == (0, 1)


def test_sm_mufredatta_kalir():
    """S3: 1 + in_mufredat=True -> (1, sayac degismez)."""
    assert calculate_next_status(1, 0, True) == (1, 0)
    assert calculate_next_status(1, 1, True) == (1, 1)


def test_sm_ilk_dusus():
    """S4: 1 + in_mufredat=False + sayac=0 -> (-1, 1)."""
    assert calculate_next_status(1, 0, False) == (-1, 1)


def test_sm_ikinci_dusus_kalici_iptal():
    """S5: 1 + in_mufredat=False + sayac=1 -> (-2, 2)."""
    assert calculate_next_status(1, 1, False) == (-2, 2)


def test_sm_havuzdan_mufredata():
    """S6: 0 + in_mufredat=True -> (1, sayac ayni)."""
    assert calculate_next_status(0, 0, True) == (1, 0)
    assert calculate_next_status(0, 1, True) == (1, 1)


def test_sm_havuzda_kalir():
    """S7: 0 + in_mufredat=False -> (0, sayac ayni)."""
    assert calculate_next_status(0, 0, False) == (0, 0)
    assert calculate_next_status(0, 1, False) == (0, 1)


def test_sm_maks_sayac_sabiti():
    """MAKS_DUSME_SAYACI = 2 olmali."""
    assert MAKS_DUSME_SAYACI == 2


def test_sm_zincir_tam():
    """2022->2023->2024->2025 tam zincir."""
    # 2022 ground truth: (1, 0) - mufredatta
    # 2023: mufredat disinda -> duser
    s23, c23 = calculate_next_status(1, 0, False)
    assert (s23, c23) == (-1, 1)

    # 2024: ceza bitti -> havuza donus (in_mufredat True olsa bile 0)
    s24, c24 = calculate_next_status(-1, 1, True)
    assert (s24, c24) == (0, 1)

    # 2025: havuzdan mufredata giriyor
    s25, c25 = calculate_next_status(0, 1, True)
    assert (s25, c25) == (1, 1)

    # 2026: tekrar dusuyor -> kalici iptal
    s26, c26 = calculate_next_status(1, 1, False)
    assert (s26, c26) == (-2, 2)


def test_sm_havuzda_sayac_artmaz():
    """Havuzdayken sayac artmamali."""
    for _ in range(5):
        s, c = calculate_next_status(0, 0, False)
        assert c == 0


def test_sm_none_guvenli():
    """None girdi -> (0, 0)."""
    s, c = calculate_next_status(None, None, False)
    assert s == 0 and c == 0


# ===========================================================================
# KISIM 2: Algoritma modulleri birim testleri
# ===========================================================================

def test_ahp_agirliklar_toplami():
    """AHP agirlik toplamı 1.0 olmali."""
    result = _run_ahp({"basari_orani": 0.7, "doluluk_orani": 0.6})
    w = result["weights"]
    total = sum(w.values())
    assert abs(total - 1.0) < 0.001, f"AHP agirlik toplami: {total}"


def test_ahp_cr_gecerli():
    """AHP tutarlilik orani < 0.10 olmali."""
    result = _run_ahp({})
    assert result.get("valid") is True


def test_topsis_skor_aralik():
    """TOPSIS skoru 0-100 arasinda olmali."""
    criteria = {
        "basari_orani": 0.75, "doluluk_orani": 0.60,
        "_trend": 0.70,
    }
    weights = {"basari": 0.5, "trend": 0.2, "populerlik": 0.2, "anket": 0.1}
    result = _run_topsis_single(criteria, weights)
    skor = result.get("score_100", -1)
    assert 0 <= skor <= 100, f"TOPSIS skor aralik disinda: {skor}"


def test_topsis_sifir_agirlik():
    """Agirlik toplamı sifira yakin -> hata yakalanmali, uygulama cokmemeli."""
    criteria = {"basari_orani": 0.7, "doluluk_orani": 0.5, "_trend": 0.6}
    weights = {"basari": 0.0, "trend": 0.0, "populerlik": 0.0, "anket": 0.0}
    result = _run_topsis_single(criteria, weights)
    assert "error" in result   # ZeroDivision yakalandı


def test_trend_bos_gecmis():
    """Gecmis veri yoksa hata vermeden varsayilan donmeli."""
    result = _run_trend([])
    assert result.get("predicted") == 0.5
    assert "Gecmis" in result.get("log", "")


def test_trend_uclu_agirlik():
    """3 yil verisi -> agirlikli ortalama hesaplamali."""
    gecmis = [
        {"yil": 2024, "oran": 0.80},
        {"yil": 2023, "oran": 0.60},
        {"yil": 2022, "oran": 0.40},
    ]
    result = _run_trend(gecmis)
    # 0.80*0.50 + 0.60*0.30 + 0.40*0.20 = 0.40+0.18+0.08 = 0.66
    assert abs(result["predicted"] - 0.66) < 0.01


def test_rf_yuksek_basari_mufredatta():
    """Yuksek basari + yuksek doluluk -> Mufredatta tahmini."""
    criteria = {"basari_orani": 0.85, "doluluk_orani": 0.70}
    prev = {"sayac": 0}
    result = _run_rf_simple(criteria, prev)
    assert result["predicted_statu"] == STATU_MUFREDATTA


def test_rf_dusuk_basari_dinlenmede():
    """Dusuk basari -> Dinlenmede tahmini."""
    criteria = {"basari_orani": 0.20, "doluluk_orani": 0.30}
    prev = {"sayac": 0}
    result = _run_rf_simple(criteria, prev)
    assert result["predicted_statu"] == STATU_DINLENMEDE


def test_rf_maks_sayac_iptal():
    """Sayac >= MAKS_DUSME_SAYACI -> Kalici Iptal."""
    criteria = {"basari_orani": 0.90, "doluluk_orani": 0.90}
    prev = {"sayac": 2}
    result = _run_rf_simple(criteria, prev)
    assert result["predicted_statu"] == STATU_IPTAL


# ===========================================================================
# KISIM 3: analyze_single_course entegrasyon-lite testleri (mock DB)
# ===========================================================================

def _make_mock_db_path(
    ders_id: int = 99,
    yil: int = 2023,
    basari_orani: float = 0.70,
    doluluk_orani: float = 0.60,
    prev_statu: int = 0,
    prev_sayac: int = 0,
    add_criteria: bool = True,
    gt_statu: int = None,       # 2022 havuz kaydı için
) -> str:
    """Gecici dosyada mock SQLite veritabani olusturur; yol dondurur (thread-safe test icin)."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ders tablosu (DersTipi kolonu ile — course_analyzer bunu PRAGMA ile tespit eder)
    cur.execute("CREATE TABLE ders (ders_id INTEGER, ad TEXT, DersTipi TEXT)")
    cur.execute("INSERT INTO ders VALUES (?,?,?)", (ders_id, "Mock Ders", "Secmeli"))


    # ders_kriterleri
    cur.execute("""CREATE TABLE ders_kriterleri (
        id INTEGER PRIMARY KEY, ders_id INTEGER, yil INTEGER, donem TEXT,
        toplam_ogrenci INTEGER, gecen_ogrenci INTEGER, basari_ortalamasi REAL,
        kontenjan INTEGER, kayitli_ogrenci INTEGER
    )""")
    if add_criteria:
        toplam = 100
        gecen  = int(toplam * basari_orani)
        kont   = 50
        kayit  = int(kont * doluluk_orani)
        cur.execute(
            "INSERT INTO ders_kriterleri VALUES (?,?,?,?,?,?,?,?,?)",
            (1, ders_id, yil, "Guz", toplam, gecen, 75.0, kont, kayit)
        )

    # performans
    cur.execute("""CREATE TABLE performans (
        id INTEGER PRIMARY KEY, ders_id INTEGER, akademik_yil INTEGER,
        donem TEXT, ortalama_not REAL, basari_orani REAL
    )""")
    if add_criteria:
        cur.execute(
            "INSERT INTO performans VALUES (?,?,?,?,?,?)",
            (1, ders_id, yil, "Guz", 75.0, basari_orani)
        )
        # Gecmis trend icin 2022
        cur.execute(
            "INSERT INTO performans VALUES (?,?,?,?,?,?)",
            (2, ders_id, 2022, "Guz", 70.0, 0.65)
        )

    # populerlik
    cur.execute("""CREATE TABLE populerlik (
        id INTEGER PRIMARY KEY, ders_id INTEGER, akademik_yil INTEGER,
        donem TEXT, talep_sayisi INTEGER, kontenjan INTEGER, doluluk_orani REAL
    )""")
    if add_criteria:
        kont = 50
        kayit = int(kont * doluluk_orani)
        cur.execute(
            "INSERT INTO populerlik VALUES (?,?,?,?,?,?,?)",
            (1, ders_id, yil, "Guz", kayit, kont, doluluk_orani)
        )

    # havuz (onceki yil)
    cur.execute("""CREATE TABLE havuz (
        id INTEGER PRIMARY KEY, ders_id TEXT, yil INTEGER, fakulte_id INTEGER,
        statu INTEGER, sayac INTEGER, skor REAL
    )""")
    prev_year = yil - 1
    cur.execute(
        "INSERT INTO havuz VALUES (?,?,?,?,?,?,?)",
        (1, str(ders_id), prev_year, 2, prev_statu, prev_sayac, 60.0)
    )
    # 2022 Ground Truth icin
    if gt_statu is not None and yil == 2022:
        cur.execute(
            "INSERT INTO havuz VALUES (?,?,?,?,?,?,?)",
            (2, str(ders_id), 2022, 2, gt_statu, 0, 70.0)
        )

    # mufredat (bos - yeterli)
    cur.execute("CREATE TABLE mufredat (mufredat_id INTEGER PRIMARY KEY, akademik_yil INTEGER)")
    cur.execute("CREATE TABLE mufredat_ders (mufredat_id INTEGER, ders_id INTEGER)")

    conn.commit()
    conn.close()
    return path


# --- Entegrasyon testleri ---

def test_analiz_veri_eksik_hata():
    """Kriter verisi olmayan ders -> error key donmeli."""
    path = _make_mock_db_path(add_criteria=False)
    try:
        result = analyze_single_course(99, 2023, path)
        assert "error" in result, "Kriter eksikken 'error' donmeli"
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def test_analiz_dict_formati_dogru():
    """Basarili analizde donus dict'i dogru anahtarlara sahip olmali."""
    path = _make_mock_db_path()
    try:
        result = analyze_single_course(99, 2023, path)
        assert "error" not in result, f"Beklenmedik hata: {result.get('error')}"
        for key in ("course", "criteria", "steps", "decision"):
            assert key in result, f"'{key}' anahtari eksik"
        for step_key in ("ahp", "trend", "topsis", "rf", "dt_reason"):
            assert step_key in result["steps"], f"steps.{step_key} eksik"
        for dec_key in ("score_final", "in_mufredat_this_year", "prev", "next", "label"):
            assert dec_key in result["decision"], f"decision.{dec_key} eksik"
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def test_analiz_statu_kodlari():
    """Yuksek basari + yuksek doluluk -> statu 1 (Mufredatta) bekleniyor."""
    path = _make_mock_db_path(
        basari_orani=0.85, doluluk_orani=0.75,
        prev_statu=0, prev_sayac=0   # havuzdan geliyorsa 0->1
    )
    try:
        result = analyze_single_course(99, 2023, path)
        assert "error" not in result
        next_statu = result["decision"]["next"]["statu"]
        assert next_statu == STATU_MUFREDATTA, f"Beklenen 1, gelen {next_statu}"
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def test_analiz_dusuk_performans_dinlenmede():
    """Dusuk basari + prev statu=1 -> -1 (Dinlenmede)."""
    path = _make_mock_db_path(
        basari_orani=0.20, doluluk_orani=0.10,
        prev_statu=1, prev_sayac=0
    )
    try:
        result = analyze_single_course(99, 2023, path)
        assert "error" not in result
        next_statu = result["decision"]["next"]["statu"]
        assert next_statu in (STATU_DINLENMEDE, STATU_IPTAL), \
            f"Beklenen -1 veya -2, gelen {next_statu}"
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def test_analiz_ikinci_dusus_kalici_iptal():
    """Prev sayac=1 + dusuyor -> statu -2 (Kalici Iptal)."""
    path = _make_mock_db_path(
        basari_orani=0.15, doluluk_orani=0.10,
        prev_statu=1, prev_sayac=1   # bir kez daha dusse kalici iptal
    )
    try:
        result = analyze_single_course(99, 2023, path)
        assert "error" not in result
        next_statu = result["decision"]["next"]["statu"]
        assert next_statu == STATU_IPTAL, f"Beklenen -2, gelen {next_statu}"
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def test_analiz_2022_ground_truth():
    """year=2022 ise state machine calismamali, mevcut havuz kaydi donmeli."""
    path = _make_mock_db_path(yil=2022, gt_statu=1)
    try:
        result = analyze_single_course(99, 2022, path)
        assert "error" not in result
        assert result["decision"]["is_ground_truth"] is True
        assert "Ground Truth" in result["decision"]["sm_note"]
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def test_analiz_db_yok():
    """Olmayan / bos veritabani yolu -> error donmeli (veya bos DB icin ders bulunamadi)."""
    # Bos SQLite dosyasi: ders tablosu yok, sorgu hata verecek
    fd, p = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        result = analyze_single_course(99, 2023, p)
        assert "error" in result, "Bos/uygunsuz DB icin error donmeli"
    finally:
        try:
            os.unlink(p)
        except OSError:
            pass


def test_analiz_ders_yok():
    """Olmayan ders_id -> error donmeli."""
    path = _make_mock_db_path(ders_id=99)
    try:
        result = analyze_single_course(9999, 2023, path)  # farkli id
        assert "error" in result
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def test_analiz_skor_aralik():
    """score_final 0-100 arasinda olmali."""
    path = _make_mock_db_path()
    try:
        result = analyze_single_course(99, 2023, path)
        if "error" not in result:
            skor = result["decision"]["score_final"]
            assert 0 <= skor <= 100, f"Skor aralik disinda: {skor}"
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


# ===========================================================================
# Manuel calistirma destegi
# ===========================================================================
if __name__ == "__main__":
    tests = [
        # State machine
        test_sm_kalici_iptal_degismez,
        test_sm_dinlenmede_havuza_donus,
        test_sm_mufredatta_kalir,
        test_sm_ilk_dusus,
        test_sm_ikinci_dusus_kalici_iptal,
        test_sm_havuzdan_mufredata,
        test_sm_havuzda_kalir,
        test_sm_maks_sayac_sabiti,
        test_sm_zincir_tam,
        test_sm_havuzda_sayac_artmaz,
        test_sm_none_guvenli,
        # Algoritma modulleri
        test_ahp_agirliklar_toplami,
        test_ahp_cr_gecerli,
        test_topsis_skor_aralik,
        test_topsis_sifir_agirlik,
        test_trend_bos_gecmis,
        test_trend_uclu_agirlik,
        test_rf_yuksek_basari_mufredatta,
        test_rf_dusuk_basari_dinlenmede,
        test_rf_maks_sayac_iptal,
        # Entegrasyon
        test_analiz_veri_eksik_hata,
        test_analiz_dict_formati_dogru,
        test_analiz_statu_kodlari,
        test_analiz_dusuk_performans_dinlenmede,
        test_analiz_ikinci_dusus_kalici_iptal,
        test_analiz_2022_ground_truth,
        test_analiz_db_yok,
        test_analiz_ders_yok,
        test_analiz_skor_aralik,
    ]

    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*55}")
    print(f"Toplam: {passed + failed} test — {passed} gecti, {failed} basarisiz")
    sys.exit(1 if failed else 0)
