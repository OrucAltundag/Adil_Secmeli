import sqlite3

def muhendislik_mufredat_durumunu_esitle(
    vt_yolu="data/adil_secmeli.db",
    baslangic_yili=2022,
    bitis_yili=2025
):
    """
    KURAL 1:
    Ders müfredatta ise
        statu = 1
        sayac = 0

    KURAL 2:
    Ders önceki yıl müfredatta idi, bu yıl yoksa
        statu = 0
        sayac += 1

    KURAL 3:
    sayac >= 2 ise
        statu = -1 (dinlenmeye alınır)

    NOT:
    Eşleştirme ders_id ile DEĞİL
    ders_adi üzerinden yapılır (senin DB yapına göre)
    """

    baglanti = sqlite3.connect(vt_yolu)
    baglanti.row_factory = sqlite3.Row
    imlec = baglanti.cursor()

    print(f"\n🔄 Müfredat → Havuz eşitleme başladı ({baslangic_yili}-{bitis_yili})")

    # -------------------------------
    # HAFIZA
    # -------------------------------
    onceki_yil_dersleri = set()

    try:
        print("🧹 Havuz sıfırlanıyor...")
        imlec.execute("UPDATE havuz SET statu = 0, sayac = 0")
        baglanti.commit()

        for yil in range(baslangic_yili, bitis_yili + 1):
            print(f"\n📅 {yil} yılı işleniyor...")

            # -----------------------------------------
            # 1️⃣ O yılın mühendislik müfredatındaki ders adları
            # -----------------------------------------
            imlec.execute("""
                SELECT DISTINCT d.ad
                FROM mufredat m
                JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
                JOIN ders d ON md.ders_id = d.ders_id
                JOIN bolum b ON m.bolum_id = b.bolum_id
                JOIN fakulte f ON b.fakulte_id = f.fakulte_id
                WHERE m.akademik_yil = ?
                  AND f.ad LIKE '%Mühendislik%'
            """, (yil,))

            mevcut_mufredat_dersleri = {
                row["ad"].strip() for row in imlec.fetchall()
            }

            print(f"  → {len(mevcut_mufredat_dersleri)} ders müfredatta")

            # -----------------------------------------
            # 2️⃣ Havuzdaki o yıla ait dersler
            # -----------------------------------------
            imlec.execute("""
                SELECT id, ders_adi, statu, sayac
                FROM havuz
                WHERE yil = ?
            """, (yil,))

            havuz_kayitlari = imlec.fetchall()

            guncellenecekler = []

            for row in havuz_kayitlari:
                havuz_id = row["id"]
                ders_adi = row["ders_adi"].strip()
                eski_statu = row["statu"]
                eski_sayac = row["sayac"]

                yeni_statu = eski_statu
                yeni_sayac = eski_sayac
                degisti = False

                # -------------------------------
                # KURAL 1 – Müfredatta
                # -------------------------------
                if ders_adi in mevcut_mufredat_dersleri:
                    if eski_statu != 1 or eski_sayac != 0:
                        yeni_statu = 1
                        yeni_sayac = 0
                        degisti = True

                # -------------------------------
                # Müfredatta DEĞİL
                # -------------------------------
                else:
                    # Önceki yıl vardı ama bu yıl yoksa
                    if ders_adi in onceki_yil_dersleri:
                        yeni_sayac += 1

                        if yeni_sayac >= 2:
                            yeni_statu = -1
                        else:
                            yeni_statu = -1

                        degisti = True

                if degisti:
                    guncellenecekler.append(
                        (yeni_statu, yeni_sayac, havuz_id)
                    )

            # -----------------------------------------
            # 3️⃣ Veritabanına yaz
            # -----------------------------------------
            if guncellenecekler:
                imlec.executemany("""
                    UPDATE havuz
                    SET statu = ?, sayac = ?
                    WHERE id = ?
                """, guncellenecekler)

                print(f"  💾 {len(guncellenecekler)} kayıt güncellendi")
            else:
                print("  ℹ️ Değişiklik yok")

            baglanti.commit()

            # -----------------------------------------
            # Hafıza güncelle
            # -----------------------------------------
            onceki_yil_dersleri = mevcut_mufredat_dersleri.copy()

        print("\n✅ Eşitleme tamamlandı")

    except sqlite3.Error as e:
        print("❌ Veritabanı hatası:", e)
        baglanti.rollback()

    finally:
        baglanti.close()
