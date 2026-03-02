# app/services/havuz_karar.py
# Havuz statü/sayaç durum makinesi (State Machine) ve müfredat-havuz eşitleme

import sqlite3

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------
STATU_MUFREDATTA = 1    # Ders o yıl aktif müfredatta
STATU_HAVUZDA    = 0    # Havuzda bekliyor; müfredata aday
STATU_DINLENMEDE = -1   # Müfredattan yeni düştü; 1 yıl ceza, seçilemez
STATU_IPTAL      = -2   # Toplamda 2 kez düştü; kalıcı olarak iptal

MAKS_DUSME_SAYACI = 2   # Bu sayıya ulaşan ders kalıcı olarak iptal edilir


# ---------------------------------------------------------------------------
# Durum Makinesi
# ---------------------------------------------------------------------------
def calculate_next_status(
    prev_statu: int,
    prev_sayac: int,
    in_mufredat_this_year: bool,
) -> tuple:
    """
    Bir önceki yılın (prev_statu, prev_sayac) durumuna ve bu yıl müfredatta
    olup olmadığına (in_mufredat_this_year) göre yeni yılın statu ve sayac
    değerini belirler.

    State Machine Kuralları:
    1. prev_statu == -2 (Kalıcı İptal)  → (-2, prev_sayac)  — değişmez.
    2. prev_statu == -1 (Dinlenmede)    → (0, prev_sayac)   — ceza bitti,
       havuza döner; in_mufredat_this_year True olsa bile bu yıl alınamaz.
    3. prev_statu == 1  (Müfredatta):
       a. in_mufredat_this_year True    → (1, prev_sayac)   — müfredatta kalır.
       b. in_mufredat_this_year False   → düşme gerçekleşir:
          yeni_sayac = prev_sayac + 1
          yeni_sayac >= MAKS_DUSME_SAYACI → (-2, yeni_sayac)
          aksi hâlde                       → (-1, yeni_sayac)
    4. prev_statu == 0  (Havuzda):
       a. in_mufredat_this_year True    → (1, prev_sayac)   — müfredata girer.
       b. in_mufredat_this_year False   → (0, prev_sayac)   — havuzda kalır.
    5. Bozuk/None değer                → (0, 0) ile başla (güvenli varsayılan).

    Sayaç SADECE statu=1 iken müfredattan düşüldüğünde artar.
    statu=0 veya statu=-1 iken sayaç KESİNLİKLE artmaz.

    :param prev_statu:           Önceki yıl statüsü  (1, 0, -1, -2)
    :param prev_sayac:           Önceki yıl düşme sayacı
    :param in_mufredat_this_year: Bu yıl ders müfredatta mı? (komisyon kararı)
    :return:                     (yeni_statu: int, yeni_sayac: int)
    """
    # Güvenli tür dönüşümü (bozuk/None girdi koruması — kural 5)
    if prev_statu is None:
        prev_statu = STATU_HAVUZDA
    if prev_sayac is None:
        prev_sayac = 0
    prev_statu = int(prev_statu)
    prev_sayac = int(prev_sayac)

    # --- Kural 1: Kalıcı iptal değişmez ---
    if prev_statu == STATU_IPTAL:
        return STATU_IPTAL, prev_sayac

    # --- Kural 2: Dinlenmedeyken 1 yıl ceza bitti, havuza döner ---
    if prev_statu == STATU_DINLENMEDE:
        return STATU_HAVUZDA, prev_sayac

    # --- Kural 3: Önceki yıl müfredattayken ---
    if prev_statu == STATU_MUFREDATTA:
        if in_mufredat_this_year:
            return STATU_MUFREDATTA, prev_sayac          # 3a: müfredatta kalır
        else:
            yeni_sayac = prev_sayac + 1                  # 3b: düşme → sayaç artar
            if yeni_sayac >= MAKS_DUSME_SAYACI:
                return STATU_IPTAL, yeni_sayac
            return STATU_DINLENMEDE, yeni_sayac

    # --- Kural 4: Önceki yıl havuzdayken ---
    if prev_statu == STATU_HAVUZDA:
        if in_mufredat_this_year:
            return STATU_MUFREDATTA, prev_sayac          # 4a: müfredata girer
        else:
            return STATU_HAVUZDA, prev_sayac             # 4b: havuzda kalır

    # Bilinmeyen statü → güvenli varsayılan
    return STATU_HAVUZDA, prev_sayac


# ---------------------------------------------------------------------------
# Yardımcı: Veritabanındaki fakülte ID'sini tespit et
# ---------------------------------------------------------------------------
def _get_muhendislik_fakulte_id(imlec) -> int:
    """Mühendislik fakültesinin ID'sini döner; bulunamazsa 2 varsayar."""
    imlec.execute("SELECT fakulte_id FROM fakulte WHERE ad LIKE '%hendislik%' LIMIT 1")
    row = imlec.fetchone()
    return int(row[0]) if row else 2


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
        fakulte_id = _get_muhendislik_fakulte_id(imlec)

        # 2022 müfredatındaki ders ID'leri (INTEGER olarak)
        imlec.execute("""
            SELECT DISTINCT md.ders_id
            FROM mufredat m
            JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
            WHERE m.akademik_yil = 2022 AND m.fakulte_id = ?
        """, (fakulte_id,))
        mufredat_ids = {int(r[0]) for r in imlec.fetchall()}

        if not mufredat_ids:
            # fakulte_id filtresi olmadan dene
            imlec.execute("""
                SELECT DISTINCT md.ders_id
                FROM mufredat m
                JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
                WHERE m.akademik_yil = 2022
            """)
            mufredat_ids = {int(r[0]) for r in imlec.fetchall()}

        print(f"   2022 mufredatinda {len(mufredat_ids)} ders var.")

        # havuz.ders_id TEXT olduğundan CAST kullanıyoruz
        # Müfredattaki dersler → statu=1, sayac=0
        if mufredat_ids:
            placeholders = ",".join(str(x) for x in mufredat_ids)
            imlec.execute(f"""
                UPDATE havuz
                SET statu = 1, sayac = 0
                WHERE yil = 2022
                  AND CAST(ders_id AS INTEGER) IN ({placeholders})
            """)
            print(f"   statu=1 yapilan: {imlec.rowcount} kayit")

        # Müfredatta olmayan dersler → statu=0, sayac=0
        if mufredat_ids:
            imlec.execute(f"""
                UPDATE havuz
                SET statu = 0, sayac = 0
                WHERE yil = 2022
                  AND CAST(ders_id AS INTEGER) NOT IN ({placeholders})
            """)
            print(f"   statu=0 yapilan: {imlec.rowcount} kayit")

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
        fakulte_id = _get_muhendislik_fakulte_id(imlec)

        # 2022'den sonra her yılı sırayla hesapla
        for hedef_yil in range(baslangic_yili + 1, bitis_yili + 1):
            onceki_yil = hedef_yil - 1
            print(f"\n[YIL] {hedef_yil} hesaplaniyor (baz: {onceki_yil})...")

            # Bu yıl müfredatta olan ders ID'leri (INTEGER SET)
            # Önce fakülte filtresiyle dene, sonuç yoksa filtresiz dene
            imlec.execute("""
                SELECT DISTINCT md.ders_id
                FROM mufredat m
                JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
                WHERE m.akademik_yil = ? AND m.fakulte_id = ?
            """, (hedef_yil, fakulte_id))
            mufredat_ids = {int(r[0]) for r in imlec.fetchall()}

            if not mufredat_ids:
                imlec.execute("""
                    SELECT DISTINCT md.ders_id
                    FROM mufredat m
                    JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
                    WHERE m.akademik_yil = ?
                """, (hedef_yil,))
                mufredat_ids = {int(r[0]) for r in imlec.fetchall()}

            print(f"   [MUFREDAT] {hedef_yil} yilinda {len(mufredat_ids)} ders var.")

            # Önceki yılın havuz kayıtları — CAST ile ders_id integer olarak alınır
            imlec.execute("""
                SELECT id, CAST(ders_id AS INTEGER) as d_id, statu, sayac, fakulte_id
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

                in_mufredat = raw_ders_id in mufredat_ids
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
                         prev_fak_id or fakulte_id)
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
                    """INSERT INTO havuz (ders_id, yil, statu, sayac, fakulte_id)
                       VALUES (?, ?, ?, ?, ?)""",
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
