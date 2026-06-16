# -*- coding: utf-8 -*-
"""Faz A regresyon testleri: yeni yil mufredat uretimi guz VE bahari birlikte uretmeli.

Spec madde 3 kilit kosulu:
- Kullanici 'Sonraki Yil Mufredat Uret' butonuna basinca G ve B birlikte calismali.
- Bahar verisi yoksa hata firlatmamali; ayrik 'skipped' bildirimi vermeli.
- Cikti spec madde 3'un beklenen alanlarini icermeli (akademik_yil, guz/bahar
  olusturuldu, ahp profili, baslangic/bitis zamani, vb.).

Bu test, dual wrapper'in calismasini ve geri uyumlu sekilde tek-donem yola
dusmemesini kilitler.
"""

from __future__ import annotations

from unittest.mock import patch


from app.services.calculation import run_all_algorithms_for_year_dual


def _stub_run(yil, db_path=None, donem="G", fakulte_id=None, strict_ahp=False):
    """run_all_algorithms_for_year'i taklit eder; cagirma argumanlarini yakalar."""
    if donem == "G":
        return {
            "ok": True,
            "year": yil,
            "processed": [{"fakulte_id": fakulte_id or 1, "message": f"Guz {yil} islendi"}],
            "skipped": [],
            "errors": [],
            "messages": ["Guz tamam"],
        }
    return {
        "ok": True,
        "year": yil,
        "processed": [{"fakulte_id": fakulte_id or 1, "message": f"Bahar {yil} islendi"}],
        "skipped": [],
        "errors": [],
        "messages": ["Bahar tamam"],
    }


def _stub_run_bahar_eksik(yil, db_path=None, donem="G", fakulte_id=None, strict_ahp=False):
    """Bahar verisi/kriteri eksik senaryosu."""
    if donem == "G":
        return {
            "ok": True,
            "year": yil,
            "processed": [{"fakulte_id": 1, "message": "Guz tamam"}],
            "skipped": [],
            "errors": [],
            "messages": ["Guz tamam"],
        }
    return {
        "ok": True,
        "year": yil,
        "processed": [],
        "skipped": [{"fakulte_id": 1, "reason": "Bahar icin kriter girisi eksik"}],
        "errors": [],
        "messages": ["Bahar atlandi"],
    }


def test_dual_wrapper_calls_both_terms():
    """Wrapper hem G hem B icin run_all_algorithms_for_year cagirmali."""
    calls = []

    def tracking_stub(yil, db_path=None, donem="G", fakulte_id=None, strict_ahp=False):
        calls.append(donem)
        return _stub_run(yil, db_path, donem, fakulte_id, strict_ahp)

    with patch("app.services.calculation.run_all_algorithms_for_year", side_effect=tracking_stub):
        result = run_all_algorithms_for_year_dual(yil=2024, fakulte_id=1)

    assert "G" in calls and "B" in calls, f"G+B birlikte cagrilmali; gercek cagri: {calls}"
    assert result["ok"] is True
    assert result["guz_olusturuldu"] is True
    assert result["bahar_olusturuldu"] is True


def test_dual_output_has_spec_fields():
    """Cikti spec madde 3 alanlarini icermeli."""
    with patch("app.services.calculation.run_all_algorithms_for_year", side_effect=_stub_run):
        result = run_all_algorithms_for_year_dual(yil=2024, fakulte_id=1)

    expected = {
        "akademik_yil", "guz_olusturuldu", "bahar_olusturuldu",
        "guz_islenen_fakulte", "bahar_islenen_fakulte",
        "guz_atlanan", "bahar_atlanan",
        "guz_hata", "bahar_hata",
        "kullanilan_ahp_profile",
        "baslangic_zaman", "bitis_zaman",
        "messages",
    }
    missing = expected - set(result.keys())
    assert not missing, f"Spec alanlari eksik: {missing}"
    assert result["akademik_yil"] == 2024
    assert isinstance(result["messages"], list) and len(result["messages"]) > 0


def test_dual_handles_missing_spring_gracefully():
    """Bahar uretilemediginde hata firlatmamali; 'skipped' ile bildirmeli."""
    with patch("app.services.calculation.run_all_algorithms_for_year", side_effect=_stub_run_bahar_eksik):
        result = run_all_algorithms_for_year_dual(yil=2024, fakulte_id=1)

    assert result["guz_olusturuldu"] is True
    assert result["bahar_olusturuldu"] is False
    assert len(result["bahar_atlanan"]) == 1
    assert "kriter" in result["bahar_atlanan"][0]["reason"].lower()
    # Bahar atlanmasi GENEL basariyi engellememeli (en az G uretildi)
    assert result["ok"] is True
    # Kullaniciya bahar nedeni mesajlarda gosterilmeli
    assert any("bahar" in m.lower() for m in result["messages"])


def test_dual_records_ahp_profile_snapshot():
    """Cikti calistirma anindaki AHP profili ozetini icermeli (izlenebilirlik)."""
    with patch("app.services.calculation.run_all_algorithms_for_year", side_effect=_stub_run):
        result = run_all_algorithms_for_year_dual(yil=2024, fakulte_id=1)

    # AHP ozet dict olmali; gercek DB calismasinda 'id' alani dolu gelir,
    # mock'lanmis testte hata yansir veya bos olabilir - alan VARSA dict olmali.
    ahp = result.get("kullanilan_ahp_profile")
    assert isinstance(ahp, dict)


def test_dual_records_start_and_end_times():
    """baslangic_zaman ve bitis_zaman ISO formatinda doldurulmali."""
    with patch("app.services.calculation.run_all_algorithms_for_year", side_effect=_stub_run):
        result = run_all_algorithms_for_year_dual(yil=2024, fakulte_id=1)

    assert "T" in result["baslangic_zaman"], "ISO timestamp bekleniyor"
    assert "T" in result["bitis_zaman"]
    assert result["baslangic_zaman"] <= result["bitis_zaman"]
