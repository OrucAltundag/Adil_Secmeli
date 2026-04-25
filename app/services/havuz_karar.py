# -*- coding: utf-8 -*-
# =============================================================================
# app/services/havuz_karar.py — Havuz Statu/Sayac Durum Makinesi
# =============================================================================
# Ders havuzu icin State Machine mantigi ve mufredat-havuz zincirleme esleme.
# Kurallar: Mufredattan dusme -> dinlenme -> tekrar aday / kalici iptal.
# =============================================================================

from __future__ import annotations

import sqlite3

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------
STATU_MUFREDATTA = 1    # Ders o yil aktif mufredatta
STATU_HAVUZDA = 0       # Havuzda bekliyor; mufredata aday
STATU_DINLENMEDE = -1   # Mufredattan yeni dustu; 1 yil ceza, secilemez
STATU_IPTAL = -2        # Toplamda 2 kez dustu; kalici olarak iptal
MAKS_DUSME_SAYACI = 2   # Bu sayiya ulasan ders kalici olarak iptal edilir

DONEM_GUZ = "Guz"
DONEM_BAHAR = "Bahar"


def normalize_semester(raw: str | None) -> str:
    value = str(raw or "").strip().lower()
    if value.startswith("b"):
        return DONEM_BAHAR
    return DONEM_GUZ


# ---------------------------------------------------------------------------
# Durum Makinesi
# ---------------------------------------------------------------------------
def calculate_next_status(
    prev_statu: int,
    prev_sayac: int,
    in_mufredat_this_year: bool,
) -> tuple[int, int]:
    """
    Bir onceki yilin (prev_statu, prev_sayac) durumuna ve bu yil mufredatta
    olup olmadigina gore yeni yilin statu ve sayac degerini belirler.
    """
    if prev_statu is None:
        prev_statu = STATU_HAVUZDA
    if prev_sayac is None:
        prev_sayac = 0
    prev_statu = int(prev_statu)
    prev_sayac = int(prev_sayac)

    if prev_statu == STATU_IPTAL:
        return STATU_IPTAL, prev_sayac

    if prev_statu == STATU_DINLENMEDE:
        return STATU_HAVUZDA, prev_sayac

    if prev_statu == STATU_MUFREDATTA:
        if in_mufredat_this_year:
            return STATU_MUFREDATTA, prev_sayac
        yeni_sayac = prev_sayac + 1
        if yeni_sayac >= MAKS_DUSME_SAYACI:
            return STATU_IPTAL, yeni_sayac
        return STATU_DINLENMEDE, yeni_sayac

    if prev_statu == STATU_HAVUZDA:
        if in_mufredat_this_year:
            return STATU_MUFREDATTA, prev_sayac
        return STATU_HAVUZDA, prev_sayac

    return STATU_HAVUZDA, prev_sayac


def calculate_next_status_semester(
    prev_statu: int,
    prev_sayac: int,
    selected_in_current_semester: bool,
    selected_in_other_semester: bool = False,
) -> tuple[int, int]:
    """
    Donem-aware durum guncellemesi.

    Bir ders ayni akademik yil icinde hem Guz hem Bahar listesinde olamaz.
    Bu kontrolu saglayip ana state machine'e delegasyon yapar.
    """
    if selected_in_current_semester and selected_in_other_semester:
        raise ValueError("Cross-semester conflict: ders ayni yil iki donemde secilemez.")

    return calculate_next_status(
        prev_statu=prev_statu,
        prev_sayac=prev_sayac,
        in_mufredat_this_year=bool(selected_in_current_semester),
    )


def calculate_next_status_governed(
    prev_statu: int,
    prev_sayac: int,
    in_mufredat_this_year: bool,
    conn: sqlite3.Connection | None = None,
    context: dict | None = None,
) -> tuple[int, int, dict]:
    """
    Geriye uyumlu adapter.

    Eski mekanik sonucu önce üretir; veritabanı bağlantısı ve bağlam verilirse
    yeni akademik yaşam döngüsü state machine'i ile recommended/final ayrımını
    hesaplar. Hata durumunda legacy sonucu bozmaz.
    """
    legacy_statu, legacy_sayac = calculate_next_status(prev_statu, prev_sayac, in_mufredat_this_year)
    payload = dict(context or {})
    payload.setdefault("legacy_recommended_status", legacy_statu)
    payload.setdefault("legacy_counter_after", legacy_sayac)
    payload.setdefault("current_status", prev_statu)
    payload.setdefault("counter_before", prev_sayac)
    payload.setdefault("in_mufredat_this_year", in_mufredat_this_year)
    if conn is None or "course_id" not in payload or "year" not in payload:
        return legacy_statu, legacy_sayac, payload
    try:
        from app.services.pool_state_machine_service import evaluate_course_state_transition

        result = evaluate_course_state_transition(conn, payload)
        return int(result["final_status"]), int(result["counter_after"]), result
    except Exception as exc:
        payload["governance_error"] = str(exc)
        return legacy_statu, legacy_sayac, payload


def enforce_cross_semester_constraints(assignments: dict[str, set[int] | list[int]]) -> dict[str, list[int]]:
    """
    Guz/Bahar listelerinde ayni dersi tekillestirir.

    Kural: cakisma varsa Guz korunur, Bahar listesinden ayni ders atilir.
    """
    guz = [int(d) for d in assignments.get(DONEM_GUZ, [])]
    bahar = [int(d) for d in assignments.get(DONEM_BAHAR, [])]
    guz_set = set(guz)
    bahar_filtered = [d for d in bahar if d not in guz_set]
    return {
        DONEM_GUZ: guz,
        DONEM_BAHAR: bahar_filtered,
    }


# ---------------------------------------------------------------------------
# Yardimci: Veritabanindaki fakulte ID'sini tespit et
# ---------------------------------------------------------------------------
def _get_muhendislik_fakulte_id(imlec) -> int:
    """Mühendislik fakültesinin ID'sini döner; bulunamazsa 2 varsayar."""
    imlec.execute("SELECT fakulte_id FROM fakulte WHERE ad LIKE '%hendislik%' LIMIT 1")
    row = imlec.fetchone()
    return int(row[0]) if row else 2


def _canonical_course_scope(imlec, ders_id: int):
    imlec.execute(
        """
        SELECT fakulte_id, bolum_id, ad
        FROM ders
        WHERE ders_id = ?
        LIMIT 1
        """,
        (int(ders_id),),
    )
    row = imlec.fetchone()
    if not row:
        return None
    return {
        "fakulte_id": int(row[0]) if row[0] is not None else None,
        "bolum_id": int(row[1]) if row[1] is not None else None,
        "ders_adi": str(row[2] or ""),
    }


def _pool_row_priority(row, canonical_fakulte_id):
    statu = int(row["statu"]) if row["statu"] is not None else 0
    score = float(row["skor"]) if row["skor"] is not None else -1.0
    row_fakulte = int(row["fakulte_id"]) if row["fakulte_id"] is not None else None
    return (
        1 if row_fakulte == canonical_fakulte_id else 0,
        1 if statu == STATU_MUFREDATTA else 0,
        score,
        -int(row["id"]),
    )


def _dedupe_havuz_year(imlec, yil: int):
    """
    Ayni yil + ders icin birden fazla havuz satiri varsa tekilleştirir.
    Kanonik kaynak: ders.fakulte_id / ders.bolum_id.
    """
    imlec.execute(
        """
        SELECT id, CAST(ders_id AS INTEGER) AS d_id, fakulte_id, bolum_id, statu, sayac, skor, ders_adi
        FROM havuz
        WHERE yil = ?
        ORDER BY id
        """,
        (int(yil),),
    )
    rows = imlec.fetchall()
    grouped = {}
    for row in rows:
        d_id = int(row["d_id"]) if row["d_id"] is not None else None
        if d_id is None:
            continue
        grouped.setdefault(d_id, []).append(row)

    updated = 0
    deleted = 0
    for ders_id, ders_rows in grouped.items():
        canonical = _canonical_course_scope(imlec, ders_id)
        canonical_fakulte_id = canonical["fakulte_id"] if canonical else None
        keep_row = max(ders_rows, key=lambda r: _pool_row_priority(r, canonical_fakulte_id))

        if canonical:
            imlec.execute(
                """
                UPDATE havuz
                SET fakulte_id = COALESCE(?, fakulte_id),
                    bolum_id = COALESCE(?, bolum_id),
                    ders_adi = CASE WHEN ? <> '' THEN ? ELSE ders_adi END
                WHERE id = ?
                """,
                (
                    canonical["fakulte_id"],
                    canonical["bolum_id"],
                    canonical["ders_adi"],
                    canonical["ders_adi"],
                    int(keep_row["id"]),
                ),
            )
            updated += int(imlec.rowcount or 0)

        for row in ders_rows:
            if int(row["id"]) == int(keep_row["id"]):
                continue
            imlec.execute("DELETE FROM havuz WHERE id = ?", (int(row["id"]),))
            deleted += int(imlec.rowcount or 0)

    return {"updated": updated, "deleted": deleted}


def _get_year_curriculum_pairs(imlec, yil: int):
    imlec.execute(
        """
        SELECT DISTINCT b.fakulte_id, md.ders_id
        FROM mufredat m
        JOIN bolum b ON b.bolum_id = m.bolum_id
        JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
        WHERE m.akademik_yil = ?
        """,
        (int(yil),),
    )
    rows = imlec.fetchall()
    pairs = {(int(row[0]), int(row[1])) for row in rows if row[0] is not None and row[1] is not None}
    if pairs:
        return pairs

    imlec.execute(
        """
        SELECT DISTINCT m.fakulte_id, md.ders_id
        FROM mufredat m
        JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
        WHERE m.akademik_yil = ?
        """,
        (int(yil),),
    )
    return {
        (int(row[0]), int(row[1]))
        for row in imlec.fetchall()
        if row[0] is not None and row[1] is not None
    }


# ---------------------------------------------------------------------------
# 2022 Ground Truth Onarımı
# ---------------------------------------------------------------------------
def onar_2022_ground_truth(vt_yolu: str = "data/adil_secmeli.db"):
    """
    2022 yılı havuz kayıtlarını müfredat verisiyle senkronize eder.

    - Müfredatta olan dersler → statu=1, sayac=0
    - Müfredatta olmayan dersler → statu=0, sayac=0  (havuzda bekliyor)

    Bu fonksiyon 2022'yi "Ground Truth" olarak kurar ve sonraki yıl
    hesaplamalarının doğru çalışması için şarttır.
    """
    baglanti = sqlite3.connect(vt_yolu)
    baglanti.row_factory = sqlite3.Row
    imlec = baglanti.cursor()

    try:
        dedupe = _dedupe_havuz_year(imlec, 2022)
        mufredat_pairs = _get_year_curriculum_pairs(imlec, 2022)

        print(f"   2022 mufredatinda {len(mufredat_pairs)} fakulte-ders eslesmesi var.")
        print(f"   2022 havuz dedupe: silinen={dedupe['deleted']} guncellenen={dedupe['updated']}")

        imlec.execute("UPDATE havuz SET statu = 0, sayac = 0 WHERE yil = 2022")
        print(f"   statu=0 yapilan: {imlec.rowcount} kayit")

        statu_1_count = 0
        for fakulte_id, ders_id in sorted(mufredat_pairs):
            imlec.execute(
                """
                UPDATE havuz
                SET statu = 1, sayac = 0
                WHERE yil = 2022
                  AND fakulte_id = ?
                  AND CAST(ders_id AS INTEGER) = ?
                """,
                (int(fakulte_id), int(ders_id)),
            )
            statu_1_count += int(imlec.rowcount or 0)
        print(f"   statu=1 yapilan: {statu_1_count} kayit")

        baglanti.commit()
        print("   2022 Ground Truth onarimi tamamlandi.")

    except Exception as e:
        baglanti.rollback()
        print(f"   Onarim hatasi: {e}")
        raise
    finally:
        baglanti.close()


# ---------------------------------------------------------------------------
# Zincirleme Yıllık Eşitleme (2022 Ground Truth → 2023 → 2024 → 2025)
# ---------------------------------------------------------------------------
def muhendislik_mufredat_durumunu_esitle(
    vt_yolu: str = "data/adil_secmeli.db",
    baslangic_yili: int = 2022,
    bitis_yili: int = 2025,
):
    """
    2022 yılını dokunmadan bırakır; 2023, 2024, 2025'i zincirleme hesaplar.

    Önce 2022 ground truth'unu onarır (müfredattaki dersler statu=1 olmalı).
    Ardından her yıl için:
      - Önceki yılın havuz kaydından (prev_statu, prev_sayac) alınır.
      - O yıl müfredatta olan ders seti CAST ile doğru JOIN ile çekilir.
      - calculate_next_status() çağrılır.
      - Sonuç havuz tablosuna batch olarak yazılır.

    2022 kayıtları (ground truth onarımı dışında) zincirleme hesapla değiştirilmez.
    Toplu sıfırlama (UPDATE ... SET statu=0) YAPILMAZ.

    NOT: havuz.ders_id TEXT, mufredat_ders.ders_id INTEGER.
         Tüm JOIN'lerde CAST(h.ders_id AS INTEGER) kullanılır.
    """
    # Önce 2022 ground truth'unu kur
    print("\n[ONARIM] 2022 Ground Truth onariliyor...")
    onar_2022_ground_truth(vt_yolu)

    baglanti = sqlite3.connect(vt_yolu)
    baglanti.row_factory = sqlite3.Row
    imlec = baglanti.cursor()

    print(f"\n[ESLEME] Mufredat -> Havuz zincirleme esleme ({baslangic_yili} GT -> {bitis_yili})")

    try:
        # 2022'den sonra her yılı sırayla hesapla
        for hedef_yil in range(baslangic_yili + 1, bitis_yili + 1):
            onceki_yil = hedef_yil - 1
            print(f"\n[YIL] {hedef_yil} hesaplaniyor (baz: {onceki_yil})...")

            prev_dedupe = _dedupe_havuz_year(imlec, onceki_yil)
            target_dedupe = _dedupe_havuz_year(imlec, hedef_yil)
            mufredat_pairs = _get_year_curriculum_pairs(imlec, hedef_yil)

            print(
                f"   [MUFREDAT] {hedef_yil} yilinda {len(mufredat_pairs)} fakulte-ders eslesmesi var. "
                f"Dedupe prev={prev_dedupe['deleted']} target={target_dedupe['deleted']}"
            )

            # Önceki yılın havuz kayıtları — CAST ile ders_id integer olarak alınır
            imlec.execute("""
                SELECT id, CAST(ders_id AS INTEGER) as d_id, statu, sayac, fakulte_id, bolum_id
                FROM havuz
                WHERE yil = ?
            """, (onceki_yil,))
            prev_kayitlar = imlec.fetchall()

            if not prev_kayitlar:
                print(f"   ⚠️ {onceki_yil} yılına ait havuz kaydı yok, atlanıyor.")
                continue

            # Bu yıl için mevcut havuz kayıtlarının haritası: int(ders_id) → havuz_id
            imlec.execute("""
                SELECT CAST(ders_id AS INTEGER), id, fakulte_id FROM havuz WHERE yil = ?
            """, (hedef_yil,))
            hedef_id_map = {}     # int(ders_id) → havuz_id
            hedef_fak_map = {}    # int(ders_id) → fakulte_id
            for r in imlec.fetchall():
                hedef_id_map[int(r[0])] = int(r[1])
                hedef_fak_map[int(r[0])] = r[2]

            guncellenecekler = []   # (yeni_statu, yeni_sayac, havuz_id)
            eklenecekler     = []   # (CAST(ders_id) AS TEXT, yil, statu, sayac, fak_id)

            sayac_istatistik = {1: 0, 0: 0, -1: 0, -2: 0}

            for row in prev_kayitlar:
                raw_ders_id = int(row["d_id"]) if row["d_id"] is not None else None
                if raw_ders_id is None:
                    continue

                prev_statu  = int(row["statu"])  if row["statu"]  is not None else 0
                prev_sayac_ = int(row["sayac"])  if row["sayac"]  is not None else 0
                prev_fak_id = row["fakulte_id"]
                prev_bol_id = row["bolum_id"]

                if prev_fak_id is None:
                    canonical = _canonical_course_scope(imlec, raw_ders_id)
                    prev_fak_id = canonical["fakulte_id"] if canonical else None
                    prev_bol_id = canonical["bolum_id"] if canonical else prev_bol_id

                in_mufredat = (int(prev_fak_id), raw_ders_id) in mufredat_pairs if prev_fak_id is not None else False
                yeni_statu, yeni_sayac = calculate_next_status(
                    prev_statu, prev_sayac_, in_mufredat
                )
                sayac_istatistik[yeni_statu] = sayac_istatistik.get(yeni_statu, 0) + 1

                if raw_ders_id in hedef_id_map:
                    guncellenecekler.append(
                        (yeni_statu, yeni_sayac, hedef_id_map[raw_ders_id])
                    )
                else:
                    # Bu yıl için kayıt yok → ekle (ders_id TEXT olarak saklanır)
                    eklenecekler.append(
                        (str(raw_ders_id), hedef_yil, yeni_statu, yeni_sayac,
                         prev_fak_id, prev_bol_id)
                    )

            # Batch güncelleme
            if guncellenecekler:
                imlec.executemany(
                    "UPDATE havuz SET statu = ?, sayac = ? WHERE id = ?",
                    guncellenecekler
                )

            # Batch ekleme
            if eklenecekler:
                imlec.executemany(
                    """INSERT INTO havuz (ders_id, yil, statu, sayac, fakulte_id, bolum_id)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    eklenecekler
                )

            baglanti.commit()
            print(f"   [OK] {len(guncellenecekler)} guncellendi, {len(eklenecekler)} eklendi.")
            print(f"      Mufredatta : {sayac_istatistik.get(1, 0)}")
            print(f"      Havuzda    : {sayac_istatistik.get(0, 0)}")
            print(f"      Dinlenmede : {sayac_istatistik.get(-1, 0)}")
            print(f"      Iptal      : {sayac_istatistik.get(-2, 0)}")

    except Exception as e:
        baglanti.rollback()
        print(f"[HATA] {e}")
        raise
    finally:
        baglanti.close()

    print("\n[TAMAM] Zincirleme esleme tamamlandi.")


def mufredat_durumunu_esitle(
    vt_yolu: str = "data/adil_secmeli.db",
    baslangic_yili: int = 2022,
    bitis_yili: int = 2025,
):
    """
    Tum fakulte ve bolumler icin zincirleme statu/sayac esitlemesi.

    Not: Islevsel olarak muhendislik_mufredat_durumunu_esitle ile ayni
    akisi kullanir; isim legacy bagimliliklarini kirmazken yeni generic
    cagri noktasini saglar.
    """
    return muhendislik_mufredat_durumunu_esitle(
        vt_yolu=vt_yolu,
        baslangic_yili=baslangic_yili,
        bitis_yili=bitis_yili,
    )




