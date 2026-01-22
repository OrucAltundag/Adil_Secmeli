import sqlite3

def muhendislik_mufredat_durumunu_esitle(vt_yolu="data/adil_secmeli.db", baslangic_yili=2022, bitis_yili=2025):
    baglanti = sqlite3.connect(vt_yolu)
    baglanti.row_factory = sqlite3.Row
    imlec = baglanti.cursor()

    print(f"\n🔄 Müfredat → Havuz durum eşitleme ({baslangic_yili}-{bitis_yili})")

    try:
        # Önce gelecek yılları (2024-2025) temizleyelim (Varsayılan 0 olsun)
        # Çünkü henüz o yılların seçimi yapılmadı, kırmızı görünmesinler.
        imlec.execute(f"UPDATE havuz SET statu = 0, sayac = 0 WHERE yil > 2023")
        baglanti.commit()

        # Ders sayaçlarını takip etmek için
        ders_sayaclari = {} 

        for yil in range(baslangic_yili, 2024): # Sadece 2022 ve 2023'ü işle
            print(f"📅 {yil} yılı kontrol ediliyor...")

            # 1. O yılın müfredatını çek
            imlec.execute("""
                SELECT d.ders_id
                FROM mufredat m
                JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
                JOIN ders d ON md.ders_id = d.ders_id
                JOIN fakulte f ON m.fakulte_id = f.fakulte_id
                WHERE m.akademik_yil = ? AND f.ad LIKE '%Mühendislik%'
            """, (yil,))
            
            mufredattakiler = {row["ders_id"] for row in imlec.fetchall()}
            
            # Debug: 2022'de müfredat bulamazsa uyar
            if yil == 2022 and not mufredattakiler:
                print("⚠️ UYARI: 2022 Müfredatı boş görünüyor!")

            # 2. O yılın havuzunu çek
            imlec.execute("SELECT id, ders_id FROM havuz WHERE yil = ?", (yil,))
            havuz_kayitlari = imlec.fetchall()
            
            guncellenecekler = []

            for row in havuz_kayitlari:
                h_id = row["id"]
                d_id = row["ders_id"]
                
                mevcut_sayac = ders_sayaclari.get(d_id, 0)
                yeni_statu = 0

                # KURAL 1: Müfredatta Var
                if d_id in mufredattakiler:
                    yeni_statu = 1
                    mevcut_sayac = 0 # Seçilince sayaç sıfırlanır
                
                # KURAL 2: Müfredatta Yok
                else:
                    # 2022 başlangıç yılı olduğu için sayaç artmaz
                    if yil > baslangic_yili:
                        mevcut_sayac += 1
                    
                    if mevcut_sayac >= 2:
                        yeni_statu = -1 # Kırmızı (Dinlenme)
                    else:
                        yeni_statu = 0  # Havuzda
                
                ders_sayaclari[d_id] = mevcut_sayac
                guncellenecekler.append((yeni_statu, mevcut_sayac, h_id))

            if guncellenecekler:
                imlec.executemany("UPDATE havuz SET statu=?, sayac=? WHERE id=?", guncellenecekler)
                print(f"   💾 {len(guncellenecekler)} kayıt güncellendi.")

            baglanti.commit()

       

    except Exception as e:
        print(f"❌ Hata: {e}")
    finally:
        baglanti.close()