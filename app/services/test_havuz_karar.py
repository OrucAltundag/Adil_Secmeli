# app/services/test_havuz_karar.py
# Havuz durum makinesi birim testleri
# Çalıştır: python -m pytest app/services/test_havuz_karar.py -v
#        veya: python app/services/test_havuz_karar.py

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.havuz_karar import (
    calculate_next_status,
    STATU_MUFREDATTA,
    STATU_HAVUZDA,
    STATU_DINLENMEDE,
    STATU_IPTAL,
    MAKS_DUSME_SAYACI,
)


# ===========================================================================
# Temel senaryolar (S1–S7)
# ===========================================================================

def test_s1_kalici_iptal_degismez():
    """S1: prev=-2 → her koşulda -2, sayaç değişmez."""
    assert calculate_next_status(-2, 2, True)  == (-2, 2)
    assert calculate_next_status(-2, 2, False) == (-2, 2)
    assert calculate_next_status(-2, 0, True)  == (-2, 0)


def test_s2_dinlenmede_0_olur_mufredat_yok_sayilir():
    """S2: prev=-1 → her koşulda 0 (in_mufredat True olsa bile)."""
    assert calculate_next_status(-1, 1, True)  == (0, 1)
    assert calculate_next_status(-1, 1, False) == (0, 1)
    assert calculate_next_status(-1, 0, True)  == (0, 0)


def test_s3_mufredatta_kalir():
    """S3: prev=1 + in_mufredat=True → (1, sayaç değişmez)."""
    assert calculate_next_status(1, 0, True) == (1, 0)
    assert calculate_next_status(1, 1, True) == (1, 1)


def test_s4_mufredattan_ilk_dusus():
    """S4: prev=1 + in_mufredat=False + prev_sayac=0 → (-1, 1)."""
    assert calculate_next_status(1, 0, False) == (-1, 1)


def test_s5_mufredattan_ikinci_dusus_kalici_iptal():
    """S5: prev=1 + in_mufredat=False + prev_sayac=1 → (-2, 2)."""
    assert calculate_next_status(1, 1, False) == (-2, 2)


def test_s6_havuzdan_mufredata():
    """S6: prev=0 + in_mufredat=True → (1, sayaç aynı)."""
    assert calculate_next_status(0, 0, True) == (1, 0)
    assert calculate_next_status(0, 1, True) == (1, 1)


def test_s7_havuzda_kalir():
    """S7: prev=0 + in_mufredat=False → (0, sayaç aynı)."""
    assert calculate_next_status(0, 0, False) == (0, 0)
    assert calculate_next_status(0, 1, False) == (0, 1)


# ===========================================================================
# Zincirleme (Time-Series) testi
# ===========================================================================

def test_zincir_tam_yasam_dongusu():
    """
    A dersi tam yaşam döngüsü:
      2022: statu=1, sayac=0  (Müfredatta — Ground Truth)
      2023: müfredattan düşer → (-1, 1)
      2024: ceza biter, havuza döner → (0, 1)   [bu yıl müfredata giremez]
      2025: müfredata alınır → (1, 1)
      → tekrar düşse: (-2, 2) — kalıcı iptal
    """
    # 2022 → 2023: müfredattan düşüyor
    statu_2023, sayac_2023 = calculate_next_status(1, 0, in_mufredat_this_year=False)
    assert statu_2023 == -1
    assert sayac_2023 == 1

    # 2023 → 2024: -1 cezası bitti, havuza döner (in_mufredat True olsa bile bu yıl 0)
    statu_2024_a, sayac_2024_a = calculate_next_status(-1, 1, in_mufredat_this_year=True)
    assert statu_2024_a == 0    # -1'den dönen yıl, müfredata giremez → 0
    assert sayac_2024_a == 1

    statu_2024_b, sayac_2024_b = calculate_next_status(-1, 1, in_mufredat_this_year=False)
    assert statu_2024_b == 0
    assert sayac_2024_b == 1

    # 2024 → 2025: havuzdan müfredata giriyor
    statu_2025, sayac_2025 = calculate_next_status(0, 1, in_mufredat_this_year=True)
    assert statu_2025 == 1
    assert sayac_2025 == 1

    # 2025 → 2026: tekrar düşüyor → kalıcı iptal
    statu_2026, sayac_2026 = calculate_next_status(1, 1, in_mufredat_this_year=False)
    assert statu_2026 == -2
    assert sayac_2026 == 2


def test_zincir_iki_dusus_direkt_iptal():
    """
    B dersi:
      2022: statu=1, sayac=0
      2023: müfredattan düşer → (-1, 1)
      2024: ceza biter → (0, 1)
      2025: müfredata girmeden havuzda kalır → (0, 1)
    """
    s23, c23 = calculate_next_status(1, 0, False)
    assert (s23, c23) == (-1, 1)

    s24, c24 = calculate_next_status(-1, 1, False)
    assert (s24, c24) == (0, 1)

    s25, c25 = calculate_next_status(0, 1, False)
    assert (s25, c25) == (0, 1)   # havuzda kalır, sayaç artmaz


def test_havuzda_sayac_artmaz():
    """Havuzdayken (statu=0) sayaç kesinlikle artmamalı."""
    for _ in range(5):
        s, c = calculate_next_status(0, 0, False)
        assert c == 0, "Havuzdayken sayaç artmamalı"


def test_dinlenmedeyken_sayac_artmaz():
    """Dinlenmedeyken (statu=-1) sayaç kesinlikle artmamalı."""
    s, c = calculate_next_status(-1, 1, False)
    assert c == 1, "Dinlenmedeyken sayaç artmamalı"
    assert s == 0


def test_none_girdi_guvenliyol():
    """None/bozuk girdi → güvenli varsayılan (0, 0)."""
    s, c = calculate_next_status(None, None, False)
    assert s == 0
    assert c == 0


def test_maks_dusme_sayaci_sabiti():
    """MAKS_DUSME_SAYACI 2 olmalı."""
    assert MAKS_DUSME_SAYACI == 2


# ===========================================================================
# Sınır testleri
# ===========================================================================

def test_sayac_tam_esik():
    """Sayaç tam eşikte (prev_sayac=1) düşünce → -2."""
    statu, sayac = calculate_next_status(1, 1, False)
    assert statu == STATU_IPTAL
    assert sayac == 2


def test_iptal_sonrasi_mufredata_girme_denemesi():
    """-2 durumundaki ders müfredata alınmak istense de -2 kalır."""
    s, c = calculate_next_status(-2, 2, True)
    assert s == -2
    assert c == 2


# ===========================================================================
# Manuel çalıştırma desteği (pytest olmadan)
# ===========================================================================
if __name__ == "__main__":
    tests = [
        test_s1_kalici_iptal_degismez,
        test_s2_dinlenmede_0_olur_mufredat_yok_sayilir,
        test_s3_mufredatta_kalir,
        test_s4_mufredattan_ilk_dusus,
        test_s5_mufredattan_ikinci_dusus_kalici_iptal,
        test_s6_havuzdan_mufredata,
        test_s7_havuzda_kalir,
        test_zincir_tam_yasam_dongusu,
        test_zincir_iki_dusus_direkt_iptal,
        test_havuzda_sayac_artmaz,
        test_dinlenmedeyken_sayac_artmaz,
        test_none_girdi_guvenliyol,
        test_maks_dusme_sayaci_sabiti,
        test_sayac_tam_esik,
        test_iptal_sonrasi_mufredata_girme_denemesi,
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
    print(f"\n{'='*50}")
    print(f"Sonuc: {passed} gecti, {failed} basarisiz")
    if failed:
        sys.exit(1)
