import sqlite3
import pandas as pd
import math
import random
import os
import traceback

# =========================================================
# 1. KARAR MOTORU (MANTIK DEĞİŞMEDİ)
# =========================================================
class KararMotoru:
    def ahp_calistir(self):
        # 4 kriter: basari, trend, populerlik, anket
        matris = [
            [1,    2,    4,    5],
            [0.5,  1,    3,    4],
            [0.25, 0.33, 1,    2],
            [0.20, 0.25, 0.50, 1]
        ]
        sutun_top = [sum(col) for col in zip(*matris)]
        agirliklar = [sum([(r[i] / (sutun_top[i] or 1)) for i in range(4)]) / 4 for r in matris]

        # normalize (garanti)
        s = sum(agirliklar) or 1.0
        agirliklar = [a / s for a in agirliklar]
        return agirliklar

    def topsis_calistir(self, df, agirliklar):
        if df.empty:
            return pd.DataFrame()

        sutunlar = ["basari", "trend", "populerlik", "anket"]
        paydalar = {c: math.sqrt(sum((float(x) ** 2) for x in df[c].fillna(0))) or 1 for c in sutunlar}

        sonuclar = []
        for _, row in df.iterrows():
            norm = []
            for i, c in enumerate(sutunlar):
                v = float(row.get(c, 0) or 0)
                norm.append((v / paydalar[c]) * float(agirliklar[i]))

            skor = sum(norm)
            sonuclar.append({
                "ders_id": int(row["ders_id"]),
                "Ders": row["ders"],
                "AHP_TOPSIS_Skor": float(skor)
            })

        return pd.DataFrame(sonuclar).sort_values(by="AHP_TOPSIS_Skor", ascending=False)


# =========================================================
# 2. VERİ YÜKLEYİCİ (HAVUZ EKLEME/SİLME YAPMAZ)
# =========================================================
def yukle_gercek_2022_mufredati(conn, excel_path):
    if not os.path.exists(excel_path):
        print(f"⚠️ Dosya yok: {excel_path}")
        return False

    print("📂 Excel Okunuyor...")
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        print(f"❌ Excel Hatası: {e}")
        return False

    df.columns = [str(c).lower().strip() for c in df.columns]
    cursor = conn.cursor()

    print("🧹 2022 Müfredat Temizliği (Havuz Korunuyor)...")
    # Sadece müfredat tablolarını temizliyoruz, havuza dokunmuyoruz.
    cursor.execute("""
        DELETE FROM mufredat_ders
        WHERE mufredat_id IN (SELECT mufredat_id FROM mufredat WHERE akademik_yil = 2022)
    """)
    cursor.execute("DELETE FROM mufredat WHERE akademik_yil = 2022")
    conn.commit()

    cursor.execute("SELECT bolum_id, ad FROM bolum")
    db_bolumler = {str(r[1]).lower().strip(): int(r[0]) for r in cursor.fetchall()}

    cursor.execute("SELECT ders_id, ad FROM ders")
    db_dersler = {str(r[1]).lower().strip(): int(r[0]) for r in cursor.fetchall()}

    cursor.execute("SELECT fakulte_id FROM fakulte WHERE ad LIKE '%Mühendislik%'")
    res = cursor.fetchone()
    fakulte_id = int(res[0]) if res else 2

    col_bolum = "bölüm"
    ders_cols = [f"seçmeli ders {i}" for i in range(1, 6)]
    count_ders = 0

    for _, row in df.iterrows():
        bolum_adi = str(row.get(col_bolum, "") or "").strip()
        if not bolum_adi:
            continue

        bolum_id = None
        bolum_adi_low = bolum_adi.lower()
        for k, v in db_bolumler.items():
            if k in bolum_adi_low or bolum_adi_low in k:
                bolum_id = v
                break
        if not bolum_id:
            continue

        cursor.execute(
            "INSERT INTO mufredat (fakulte_id, bolum_id, akademik_yil, donem, durum) VALUES (?, ?, 2022, 'Güz', 'Resmi')",
            (fakulte_id, bolum_id)
        )
        muf_id = cursor.lastrowid

        for col in ders_cols:
            if col not in df.columns:
                continue
            raw = row.get(col)
            if pd.isna(raw) or str(raw).strip() == "":
                continue

            d_key = str(raw).strip().lower()
            d_id = db_dersler.get(d_key)

            if not d_id:
                # yakın eşleşme dene
                for k, v in db_dersler.items():
                    if d_key == k:
                        d_id = v
                        break

            if d_id:
                # Müfredata ekle (Burası serbest)
                cursor.execute(
                    "INSERT OR IGNORE INTO mufredat_ders (mufredat_id, ders_id) VALUES (?, ?)",
                    (muf_id, d_id)
                )

                # --- GÜVENLİ MOD: SADECE UPDATE ---
                # Havuza yeni satır eklemiyoruz. Sadece varsa güncelliyoruz.
                cursor.execute(
                    "UPDATE havuz SET statu = 1, sayac = 0 WHERE ders_id = ? AND fakulte_id = ? AND yil = 2022",
                    (d_id, fakulte_id)
                )
                
                # İpucu: Eğer havuzda bu ders yoksa, yukarıdaki komut hiçbir şey yapmaz (hata vermez).
                # Bu tam olarak istediğimiz şey.

                # 2022 performans verilerini oluştur (Performans tablosu havuza dahil değil, o yüzden burası kalabilir)
                cursor.execute(
                    "SELECT count(*) FROM performans WHERE ders_id=? AND akademik_yil=2022",
                    (d_id,)
                )
                if cursor.fetchone()[0] == 0:
                    ort = random.uniform(50, 95)
                    talep = int(50 * random.uniform(0.5, 1.5))
                    cursor.execute(
                        "INSERT INTO performans (ders_id, akademik_yil, ortalama_not, basari_orani) VALUES (?, 2022, ?, ?)",
                        (d_id, ort, ort / 100)
                    )
                    cursor.execute(
                        "INSERT INTO populerlik (ders_id, akademik_yil, talep_sayisi, kontenjan, doluluk_orani) VALUES (?, 2022, ?, 50, ?)",
                        (d_id, talep, min(talep / 50, 1.0))
                    )
                    cursor.execute(
                        "INSERT INTO skor (ders_id, akademik_yil, skor_top) VALUES (?, 2022, 0)",
                        (d_id,)
                    )

                count_ders += 1

    conn.commit()
    print(f"✅ 2022 Hazır: {count_ders} ders işlendi (Havuz yapısı bozulmadan güncellendi).")
    return True


# =========================================================
# 3. ANA OTOMASYON (GÜVENLİ MOD)
# =========================================================
def run_automatic_scoring(db_path="data/adil_secmeli.db"):
    conn = None
    try:
        if not os.path.exists(db_path):
            print(f"⚠️ DB yok: {db_path}")
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print("⚙️  İşlem Başlıyor (GÜVENLİ MOD: Ekleme/Silme Yok)...")

        # 1) 2022 yükle
        excel_path = os.path.join(os.path.dirname(db_path), "2022_Mufredat.xlsx")
        if not yukle_gercek_2022_mufredati(conn, excel_path):
            return

        # 2) 2023+ Temizlik
        print("🧹 2023+ Müfredat Temizliği...")
        cursor.execute("""
            DELETE FROM mufredat_ders
            WHERE mufredat_id IN (SELECT mufredat_id FROM mufredat WHERE akademik_yil > 2022)
        """)
        cursor.execute("DELETE FROM mufredat WHERE akademik_yil > 2022")
        
        # --- ÖNEMLİ: Havuzdan silme işlemi iptal edildi ---
        # cursor.execute("DELETE FROM havuz WHERE yil > 2022")  <-- SİLİNDİ
        
        conn.commit()

        # 3) 2023 Veri Simülasyonu (Performans tablosu serbest)
        print("🎲 2023 Puanları...")
        cursor.execute("SELECT ders_id, ortalama_not FROM performans WHERE akademik_yil=2022")
        rows_2022 = cursor.fetchall()

        for d_id, not_22 in rows_2022:
            yeni_not = max(30, min(100, float(not_22) + random.uniform(-15, 15)))
            talep = int(50 * random.uniform(0.6, 1.4))

            cursor.execute(
                "INSERT INTO performans (ders_id, akademik_yil, ortalama_not, basari_orani) VALUES (?, 2023, ?, ?)",
                (d_id, yeni_not, yeni_not / 100)
            )
            cursor.execute(
                "INSERT INTO populerlik (ders_id, akademik_yil, talep_sayisi, kontenjan, doluluk_orani) VALUES (?, 2023, ?, 50, ?)",
                (d_id, talep, min(talep / 50, 1.0))
            )
        conn.commit()

        # 4) Hesaplama
        fakulte_id = 2  # mühendislik id sende farklıysa burayı ayarla
        motor = KararMotoru()
        agirliklar = motor.ahp_calistir()

        # Ders tipi kolon adı tespiti
        try:
            cursor.execute("SELECT 1 FROM ders WHERE DersTipi='Seçmeli' LIMIT 1")
            col_tip = "DersTipi"
        except Exception:
            col_tip = "tip"

        # Havuz geçmişi (2022)
        ders_gecmisi = {}
        cursor.execute("SELECT ders_id, statu FROM havuz WHERE yil=2022 AND fakulte_id=?", (fakulte_id,))
        for d_id, st in cursor.fetchall():
            ders_gecmisi[int(d_id)] = int(st)

        # Ana veri sorgusu (2023)
        query = f"""
            SELECT d.ders_id, d.ad, p.basari_orani, pop.doluluk_orani
            FROM ders d
            LEFT JOIN performans p ON d.ders_id = p.ders_id AND p.akademik_yil = 2023
            LEFT JOIN populerlik pop ON d.ders_id = pop.ders_id AND pop.akademik_yil = 2023
            WHERE d.fakulte_id = ? AND d.{col_tip}='Seçmeli'
        """
        cursor.execute(query, (fakulte_id,))
        rows_main = cursor.fetchall() 

        # 2023 ortalama_not sözlüğü
        not_sozlugu = {}
        cursor.execute("SELECT ders_id, ortalama_not FROM performans WHERE akademik_yil=2023")
        for d_id, ort in cursor.fetchall():
            not_sozlugu[int(d_id)] = float(ort)

        raw_data = []
        for (d_id, d_ad, bas, dol) in rows_main:
            d_id = int(d_id)
            d_ad = str(d_ad or "")

            bas = float(bas) if bas is not None else 0.5
            dol = float(dol) if dol is not None else 0.5

            # dinlenmedekileri dahil etme
            if ders_gecmisi.get(d_id) == -1:
                continue

            raw_data.append({
                "ders_id": d_id,
                "ders": d_ad,
                "basari": bas,
                "populerlik": dol,
                "trend": 0.5,
                "anket": 0.5
            })

        df_sonuc = motor.topsis_calistir(pd.DataFrame(raw_data), agirliklar)
        ders_skorlari = {int(r["ders_id"]): float(r["AHP_TOPSIS_Skor"]) for _, r in df_sonuc.iterrows()}

        # 5) 2023 Müfredat oluştur (bölüm bazlı)
        cursor.execute("SELECT bolum_id, ad FROM bolum WHERE fakulte_id=?", (fakulte_id,))
        bolumler = cursor.fetchall()

        tum_dusenler = set()

        for bolum_id, bolum_adi in bolumler:
            bolum_id = int(bolum_id)
            bolum_adi = str(bolum_adi or "")

            cursor.execute(
                "INSERT INTO mufredat (fakulte_id, bolum_id, akademik_yil, donem, durum) VALUES (?, ?, 2023, 'Güz', 'Otomatik')",
                (fakulte_id, bolum_id)
            )
            muf_id = cursor.lastrowid

            # 2022 bölüm müfredatı
            cursor.execute("""
                SELECT md.ders_id
                FROM mufredat m
                JOIN mufredat_ders md ON m.mufredat_id=md.mufredat_id
                WHERE m.bolum_id=? AND m.akademik_yil=2022
            """, (bolum_id,))
            gecen_yilki_dersler = [int(r[0]) for r in cursor.fetchall()]
            if not gecen_yilki_dersler:
                continue

            # adaylar: en düşük skorlu ders düşsün
            adaylar = [(d_id, ders_skorlari.get(d_id, 0.0)) for d_id in gecen_yilki_dersler]
            adaylar.sort(key=lambda x: x[1])

            dusen_ders = adaylar[0][0]
            kalan_dersler = [x[0] for x in adaylar[1:]]
            tum_dusenler.add(dusen_ders)

            # dışarıdan yeni ders bul
            girecek_ders = None
            if not df_sonuc.empty:
                for _, row in df_sonuc.iterrows():
                    aday_id = int(row["ders_id"])
                    if aday_id not in gecen_yilki_dersler and aday_id != dusen_ders:
                        if not_sozlugu.get(aday_id, 0) >= 50:
                            girecek_ders = aday_id
                            break

            if girecek_ders:
                kalan_dersler.append(girecek_ders)
                if "Bilgisayar" in bolum_adi:
                    print(f"   🔄 {bolum_adi}: Çıkan ID:{dusen_ders} -> Giren ID:{girecek_ders}")
            else:
                kalan_dersler.append(dusen_ders)

            for d_id in kalan_dersler:
                cursor.execute(
                    "INSERT OR IGNORE INTO mufredat_ders (mufredat_id, ders_id) VALUES (?, ?)",
                    (muf_id, int(d_id))
                )

        conn.commit()

        # =========================================================
        # 6) HAVUZU 2023 için GÜNCELLE (INSERT YOK, SADECE UPDATE)
        # =========================================================

        # 6.1) 2023 müfredattaki tüm dersleri topla
        tum_secilenler_db = set()
        cursor.execute("""
            SELECT DISTINCT md.ders_id
            FROM mufredat m
            JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
            WHERE m.akademik_yil = 2023 AND m.fakulte_id = ?
        """, (fakulte_id,))
        for (d_id,) in cursor.fetchall():
            tum_secilenler_db.add(int(d_id))

        # 6.2) Fakültedeki tüm seçmeli dersler üzerinden havuz kayıtlarını UPDATE et
        cursor.execute(f"SELECT ders_id FROM ders WHERE fakulte_id=? AND {col_tip}='Seçmeli'", (fakulte_id,))
        all_electives = [int(r[0]) for r in cursor.fetchall()]

        updated_count = 0
        for d_id in all_electives:
            skor = float(ders_skorlari.get(d_id, 0.5))

            if d_id in tum_secilenler_db:
                statu = 1
                sayac = 0
            elif d_id in tum_dusenler:
                statu = -1
                sayac = 1
            else:
                statu = 0
                sayac = 0
                skor = 0.5

            # --- GÜVENLİ GÜNCELLEME ---
            # INSERT yok. Sadece havuzda hali hazırda var olan dersin durumunu güncelliyoruz.
            cursor.execute("""
                UPDATE havuz
                SET statu = ?, sayac = ?, skor = ?
                WHERE ders_id = ? AND fakulte_id = ? AND yil = 2023
            """, (statu, sayac, skor, d_id, fakulte_id))
            
            if cursor.rowcount > 0:
                updated_count += 1

        conn.commit()

        # 6.3) ✅ ASIL GARANTİ: (Sadece var olan kayıtlar üzerinde çalışır)
        cursor.execute("""
            UPDATE havuz
            SET statu = 1, sayac = 0
            WHERE yil = 2023 AND fakulte_id = ?
              AND ders_id IN (
                SELECT DISTINCT md.ders_id
                FROM mufredat m
                JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
                WHERE m.akademik_yil = 2023 AND m.fakulte_id = ?
              )
        """, (fakulte_id, fakulte_id))
        conn.commit()

        print(f"✅ 2023 Tamamlandı. ({updated_count} ders güncellendi. Ekleme yapılmadı.)")

    except Exception as e:
        print(f"❌ HATA: {e}")
        traceback.print_exc()
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    run_automatic_scoring()