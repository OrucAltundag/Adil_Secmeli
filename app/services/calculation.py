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
    def __init__(self, db=None):
        self.db = db

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

        s = sum(agirliklar) or 1.0
        agirliklar = [a / s for a in agirliklar]
        # Garanti: toplam 1.0 olsun (float rounding)
        toplam = sum(agirliklar)
        if toplam and abs(toplam - 1.0) > 1e-6:
            agirliklar = [a / toplam for a in agirliklar]
        return agirliklar

    def gecmis_trend_hesapla(self, gecmis_list):
        """
        Geçmiş yılların ağırlıklı ortalamasını hesaplar.
        gecmis_list: [{"yil": 2024, "oran": 0.85}, {"yil": 2023, "oran": 0.70}, ...]
        En yeni yıl en yüksek ağırlığı alır.
        Döner: (trend_skoru_float, log_mesaji_str)
        """
        if not gecmis_list:
            return 0.0, "Geçmiş veri yok."

        agirlik_sirasi = [0.50, 0.30, 0.20]
        toplam_agirlik = 0.0
        toplam_puan = 0.0
        log_parcalari = []

        for i, item in enumerate(gecmis_list):
            agirlik = agirlik_sirasi[i] if i < len(agirlik_sirasi) else 0.0
            oran = float(item.get("oran", 0) or 0)
            puan = oran * agirlik
            toplam_puan += puan
            toplam_agirlik += agirlik
            log_parcalari.append(f"{item['yil']}: %{oran*100:.1f} x {agirlik:.0%}")

        trend = toplam_puan / toplam_agirlik if toplam_agirlik > 0 else 0.0
        log = " | ".join(log_parcalari) + f"  -> Trend: {trend:.4f}"
        return trend, log

    def topsis_calistir(self, df, agirliklar):
        if df.empty:
            return pd.DataFrame(), {}

        sutunlar = ["basari", "trend", "populerlik", "anket"]
        # Ağırlık normalizasyonu (toplam 1.0)
        w_sum = sum(agirliklar) or 1.0
        agirliklar = [float(a) / w_sum for a in agirliklar]

        # Sıfıra bölünme koruması: payda en az 1e-10
        def _safe_div(num, denom, default=0.0):
            return num / denom if denom and abs(denom) > 1e-10 else default

        paydalar = {}
        for c in sutunlar:
            sq_sum = sum((float(x) ** 2) for x in df[c].fillna(0))
            paydalar[c] = math.sqrt(sq_sum) if sq_sum > 1e-10 else 1.0

        ideal = {c: max([float(x) for x in df[c].fillna(0)] or [0.0]) for c in sutunlar}
        anti_ideal = {c: min([float(x) for x in df[c].fillna(0)] or [0.0]) for c in sutunlar}

        sonuclar = []
        for _, row in df.iterrows():
            norm_agirlikli = {}
            for i, c in enumerate(sutunlar):
                v = float(row.get(c, 0) or 0)
                norm_agirlikli[c] = _safe_div(v, paydalar[c], 0.0) * float(agirliklar[i])

            s_plus = math.sqrt(sum(
                (norm_agirlikli[c] - _safe_div(ideal[c], paydalar[c], 0) * agirliklar[i]) ** 2
                for i, c in enumerate(sutunlar)
            ))
            s_minus = math.sqrt(sum(
                (norm_agirlikli[c] - _safe_div(anti_ideal[c], paydalar[c], 0) * agirliklar[i]) ** 2
                for i, c in enumerate(sutunlar)
            ))

            denom = s_plus + s_minus
            topsis_skor = _safe_div(s_minus, denom, 0.0)

            sonuclar.append({
                "ders_id": int(row["ders_id"]) if "ders_id" in row else 0,
                "Ders": row.get("ders", ""),
                "AHP_TOPSIS_Skor": float(topsis_skor),
                "S+": round(s_plus, 6),
                "S-": round(s_minus, 6),
            })

        df_sonuc = pd.DataFrame(sonuclar).sort_values(by="AHP_TOPSIS_Skor", ascending=False)
        meta = {"agirliklar": agirliklar, "sutunlar": sutunlar}
        return df_sonuc, meta


def ders_cakisma_kontrolu(ders_listesi, conn=None):
    """
    Aynı gün ve saatte çakışan dersleri tespit eder.
    ders_listesi: [(ders_id, gun, baslangic_saati, bitis_saati), ...]
    Döner: [(ders_id_a, ders_id_b), ...] çakışan çiftler
    """
    if not ders_listesi or len(ders_listesi) < 2:
        return []

    def _saat_dakika(s):
        if not s:
            return 0, 0
        s = str(s).strip()
        if ":" in s:
            p = s.split(":")
            return int(p[0] or 0), int(p[1] or 0)
        try:
            return int(float(s)), 0
        except (ValueError, TypeError):
            return 0, 0

    def _cakisma(gun1, b1, e1, gun2, b2, e2):
        if (gun1 or "").strip() != (gun2 or "").strip():
            return False
        sb1, sm1 = _saat_dakika(b1)
        se1, em1 = _saat_dakika(e1)
        sb2, sm2 = _saat_dakika(b2)
        se2, em2 = _saat_dakika(e2)
        dk1_bas = sb1 * 60 + sm1
        dk1_bit = se1 * 60 + em1
        dk2_bas = sb2 * 60 + sm2
        dk2_bit = se2 * 60 + em2
        return not (dk1_bit <= dk2_bas or dk2_bit <= dk1_bas)

    cakisanlar = []
    for i in range(len(ders_listesi)):
        for j in range(i + 1, len(ders_listesi)):
            d1, d2 = ders_listesi[i], ders_listesi[j]
            if len(d1) >= 4 and len(d2) >= 4:
                if _cakisma(d1[1], d1[2], d1[3], d2[1], d2[2], d2[3]):
                    cakisanlar.append((d1[0], d2[0]))
    return cakisanlar


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
                    kontenjan = 50
                    doluluk = min(talep / (kontenjan or 1), 1.0)
                    cursor.execute(
                        "INSERT INTO populerlik (ders_id, akademik_yil, talep_sayisi, kontenjan, doluluk_orani) VALUES (?, 2022, ?, ?, ?)",
                        (d_id, talep, kontenjan, doluluk)
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
            kontenjan = 50
            doluluk = min(talep / (kontenjan or 1), 1.0)
            cursor.execute(
                "INSERT INTO populerlik (ders_id, akademik_yil, talep_sayisi, kontenjan, doluluk_orani) VALUES (?, 2023, ?, ?, ?)",
                (d_id, talep, kontenjan, doluluk)
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

        df_sonuc, _ = motor.topsis_calistir(pd.DataFrame(raw_data), agirliklar)
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