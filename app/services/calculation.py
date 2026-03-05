# =============================================================================
# app/services/calculation.py — Karar Motoru (AHP, TOPSIS) ve Otomatik Puanlama
# =============================================================================
# Bu modül: performans + populerlik tablolarından veri okuyarak AHP ağırlıkları
# ve TOPSIS sıralaması hesaplar. run_automatic_scoring ile otomatik skor atama yapar.
# İlgili: criteria_page (kriter girişi), havuz_karar (statü güncelleme)
# =============================================================================

import sqlite3
import pandas as pd
import math
import random
import os
import traceback
from app.services.havuz_karar import calculate_next_status

# ---------- BÖLÜM 1: Karar Motoru (AHP + TOPSIS) ----------
# AHP için RI (Random Index) - 4 kriter için
RI_4 = 0.90

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
        return agirliklar

    def ahp_tutarlilik_kontrolu(self, matris=None, agirliklar=None):
        """
        Tutarlılık Oranı (CR) hesaplar. CR < 0.10 kabul edilebilir.
        Döner: (cr: float, gecerli: bool, lambda_max: float)
        """
        if matris is None:
            matris = [
                [1, 2, 4, 5], [0.5, 1, 3, 4],
                [0.25, 0.33, 1, 2], [0.20, 0.25, 0.50, 1]
            ]
        if agirliklar is None:
            agirliklar = self.ahp_calistir()
        n = len(matris)
        weighted_sum = [sum(matris[i][j] * agirliklar[j] for j in range(n)) for i in range(n)]
        lambda_vals = [weighted_sum[i] / (agirliklar[i] or 1e-10) for i in range(n)]
        lambda_max = sum(lambda_vals) / n
        ci = (lambda_max - n) / (n - 1) if n > 1 else 0
        cr = ci / RI_4 if RI_4 else 0
        return cr, cr < 0.10, lambda_max

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
        """
        TOPSIS: Veri akışı AHP'den gelen ağırlıklarla.
        1) Karekök toplamları ile normalize
        2) Ağırlıklı normalize matris
        3) Pozitif/Negatif ideal çözümler
        4) Öklid uzaklıkları
        5) Yakınlık Katsayısı (0-1)
        """
        if df.empty:
            return pd.DataFrame(), {}

        def _safe_div(a, b, default=0.0):
            return a / b if b and abs(b) > 1e-10 else default

        sutunlar = ["basari", "trend", "populerlik", "anket"]
        w_sum = sum(agirliklar) or 1.0
        w = [float(a) / w_sum for a in agirliklar]

        # 1. Vector normalization: r_ij = x_ij / sqrt(sum(x_ij^2))
        sqrt_sums = {}
        for c in sutunlar:
            sq = sum((float(x) ** 2) for x in df[c].fillna(0))
            sqrt_sums[c] = math.sqrt(sq) if sq > 1e-10 else 1.0

        R = df.copy()
        for c in sutunlar:
            R[c] = df[c].fillna(0).apply(lambda x: _safe_div(float(x), sqrt_sums[c], 0.0))

        # 2. Ağırlıklı matris: V_ij = w_j * r_ij
        V = pd.DataFrame()
        for i, c in enumerate(sutunlar):
            V[c] = R[c] * w[i]

        # 3. İdeal çözümler (tüm kriterler "ne kadar yüksek o kadar iyi")
        A_plus = {c: V[c].max() for c in sutunlar}
        A_minus = {c: V[c].min() for c in sutunlar}

        sonuclar = []
        for i, (idx, row) in enumerate(df.iterrows()):
            v_row = V.iloc[i]
            s_plus = math.sqrt(sum((v_row[c] - A_plus[c]) ** 2 for c in sutunlar))
            s_minus = math.sqrt(sum((v_row[c] - A_minus[c]) ** 2 for c in sutunlar))
            denom = s_plus + s_minus
            ci = _safe_div(s_minus, denom, 0.0)
            skor_100 = ci * 100
            sonuclar.append({
                "ders_id": int(row["ders_id"]) if "ders_id" in row else 0,
                "Ders": row.get("ders", ""),
                "AHP_TOPSIS_Skor": round(ci, 6),
                "Kesinlesme_Puani": round(skor_100, 2),
                "S+": round(s_plus, 6),
                "S-": round(s_minus, 6),
            })

        df_sonuc = pd.DataFrame(sonuclar).sort_values(by="AHP_TOPSIS_Skor", ascending=False)
        meta = {"agirliklar": w, "sutunlar": sutunlar, "A_plus": A_plus, "A_minus": A_minus}
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

        # Anket oranları (ders_kriterleri: anket_dersi_secen/anket_katilimci)
        anket_sozlugu = {}
        try:
            cursor.execute(
                "SELECT ders_id, anket_katilimci, anket_dersi_secen FROM ders_kriterleri WHERE yil=2023"
            )
            for d_id, kat, sec in cursor.fetchall():
                if kat and kat > 0 and sec is not None:
                    anket_sozlugu[int(d_id)] = min(1.0, max(0.0, float(sec) / float(kat)))
                else:
                    anket_sozlugu[int(d_id)] = 0.5
        except sqlite3.OperationalError:
            pass  # anket sütunları yoksa atla

        raw_data = []
        for (d_id, d_ad, bas, dol) in rows_main:
            d_id = int(d_id)
            d_ad = str(d_ad or "")

            bas = float(bas) if bas is not None else 0.5
            dol = float(dol) if dol is not None else 0.5
            anket = anket_sozlugu.get(d_id, 0.5)

            # dinlenmedekileri dahil etme
            if ders_gecmisi.get(d_id) == -1:
                continue

            raw_data.append({
                "ders_id": d_id,
                "ders": d_ad,
                "basari": bas,
                "populerlik": dol,
                "trend": 0.5,
                "anket": anket
            })

        df_sonuc, _ = motor.topsis_calistir(pd.DataFrame(raw_data), agirliklar)
        # Kesinleşme Puanı (0-100) varsa onu kullan; yoksa AHP_TOPSIS_Skor (0-1) * 100
        ders_skorlari = {}
        for _, r in df_sonuc.iterrows():
            d_id = int(r["ders_id"])
            puani = r.get("Kesinlesme_Puani")
            if puani is not None and not (isinstance(puani, float) and math.isnan(puani)):
                ders_skorlari[d_id] = float(puani)
            else:
                raw = r.get("AHP_TOPSIS_Skor", 0.5)
                ders_skorlari[d_id] = float(raw) * 100.0 if raw is not None else 50.0

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

        # havuz.ders_id TEXT tipinde olduğundan CAST(ders_id AS INTEGER) kullanılır
        updated_count = 0
        for d_id in all_electives:
            skor = ders_skorlari.get(d_id, 50.0)
            if skor is None or (isinstance(skor, float) and math.isnan(skor)):
                skor = 50.0
            skor = float(skor)

            if d_id in tum_secilenler_db:
                statu = 1
                sayac = 0
            elif d_id in tum_dusenler:
                statu = -1
                sayac = 1
            else:
                statu = 0
                sayac = 0
                skor = 50.0

            # havuz.ders_id TEXT — CAST ile eşleştirme
            cursor.execute("""
                UPDATE havuz
                SET statu = ?, sayac = ?, skor = ?
                WHERE CAST(ders_id AS INTEGER) = ?
                  AND fakulte_id = ? AND yil = 2023
            """, (statu, sayac, skor, d_id, fakulte_id))

            if cursor.rowcount > 0:
                updated_count += 1

        conn.commit()

        # 6.3) Güvence: mufredat tablosundaki 2023 derslerini statu=1 garantile
        cursor.execute("""
            UPDATE havuz
            SET statu = 1, sayac = 0
            WHERE yil = 2023 AND fakulte_id = ?
              AND CAST(ders_id AS INTEGER) IN (
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



def _safe_float2(value, default=0.0):
    try:
        if value is None:
            return float(default)
        val = float(value)
        if math.isnan(val) or math.isinf(val):
            return float(default)
        return val
    except (TypeError, ValueError):
        return float(default)


def _resolve_elective_col(cur):
    cur.execute("PRAGMA table_info(ders)")
    cols = {str(r[1]) for r in cur.fetchall()}
    if "DersTipi" in cols:
        return "DersTipi"
    if "tip" in cols:
        return "tip"
    return None


def _has_full_criteria(cur, ders_id, yil, donem):
    try:
        cur.execute(
            """
            SELECT toplam_ogrenci, gecen_ogrenci, kontenjan, kayitli_ogrenci
            FROM ders_kriterleri
            WHERE ders_id = ? AND yil = ?
              AND (COALESCE(TRIM(donem), '') = '' OR LOWER(SUBSTR(TRIM(donem), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1)))
            ORDER BY CASE WHEN LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1)) THEN 0 ELSE 1 END, id DESC
            LIMIT 1
            """,
            (int(ders_id), int(yil), str(donem), str(donem)),
        )
        row = cur.fetchone()
        if not row:
            return False
        toplam = _safe_float2(row[0], 0.0)
        gecen = _safe_float2(row[1], 0.0)
        kontenjan = _safe_float2(row[2], 0.0)
        kayitli = _safe_float2(row[3], 0.0)
        return toplam > 0 and kontenjan > 0 and gecen >= 0 and kayitli >= 0
    except Exception:
        return False


def _read_course_metrics(cur, ders_id, yil, donem, motor):
    cur.execute(
        """
        SELECT toplam_ogrenci, gecen_ogrenci, basari_ortalamasi,
               kontenjan, kayitli_ogrenci, anket_katilimci, anket_dersi_secen
        FROM ders_kriterleri
        WHERE ders_id = ? AND yil = ?
          AND (COALESCE(TRIM(donem), '') = '' OR LOWER(SUBSTR(TRIM(donem), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1)))
        ORDER BY CASE WHEN LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1)) THEN 0 ELSE 1 END, id DESC
        LIMIT 1
        """,
        (int(ders_id), int(yil), str(donem), str(donem)),
    )
    dk = cur.fetchone()

    cur.execute(
        """
        SELECT basari_orani
        FROM performans
        WHERE ders_id = ? AND akademik_yil = ?
        ORDER BY pfrs_id DESC
        LIMIT 1
        """,
        (int(ders_id), int(yil)),
    )
    pf = cur.fetchone()

    cur.execute(
        """
        SELECT doluluk_orani
        FROM populerlik
        WHERE ders_id = ? AND akademik_yil = ?
        ORDER BY pop_id DESC
        LIMIT 1
        """,
        (int(ders_id), int(yil)),
    )
    pop = cur.fetchone()

    basari = _safe_float2(pf[0] if pf else None, 0.0)
    doluluk = _safe_float2(pop[0] if pop else None, 0.0)
    anket = 0.5

    if dk:
        toplam = _safe_float2(dk[0], 0.0)
        gecen = _safe_float2(dk[1], 0.0)
        kontenjan = _safe_float2(dk[3], 0.0)
        kayitli = _safe_float2(dk[4], 0.0)
        if toplam > 0:
            basari = gecen / toplam
        if kontenjan > 0:
            doluluk = kayitli / kontenjan

        anket_kat = _safe_float2(dk[5], 0.0)
        anket_secen = _safe_float2(dk[6], 0.0)
        if anket_kat > 0:
            anket = max(0.0, min(1.0, anket_secen / anket_kat))

    basari = max(0.0, min(1.0, basari))
    doluluk = max(0.0, min(1.0, doluluk))

    cur.execute(
        """
        SELECT akademik_yil, basari_orani
        FROM performans
        WHERE ders_id = ? AND akademik_yil <= ? AND basari_orani IS NOT NULL
        ORDER BY akademik_yil DESC
        LIMIT 3
        """,
        (int(ders_id), int(yil)),
    )
    gecmis = [{"yil": int(r[0]), "oran": _safe_float2(r[1], basari)} for r in cur.fetchall()]
    trend, _ = motor.gecmis_trend_hesapla(gecmis) if gecmis else (basari, "")
    trend = max(0.0, min(1.0, _safe_float2(trend, basari)))

    return {
        "ders_id": int(ders_id),
        "basari": basari,
        "trend": trend,
        "populerlik": doluluk,
        "anket": max(0.0, min(1.0, _safe_float2(anket, 0.5))),
    }


def generate_next_year_curricula(
    db_path="data/adil_secmeli.db",
    fakulte_id=None,
    akademik_yil=None,
    donem="G",
    drop_score_threshold=40.0,
):
    """
    Faculty + year + term icin bolum bazli sonraki yil mufredati olusturur.
    - Tum bolumlerin mevcut mufredat dersleri icin kriter girisi zorunludur.
    - Dusen dersler (skor baraj altinda) yerine kesinlesme puani en yuksek adaylar eklenir.
    - Duser yoksa mufredat aynen bir sonraki yila tasinir.
    - Havuz statu/sayac guncellemesi calculate_next_status ile yapilir.
    """
    if fakulte_id is None or akademik_yil is None:
        return {
            "ok": False,
            "error": "fakulte_id ve akademik_yil zorunludur.",
        }

    fakulte_id = int(fakulte_id)
    akademik_yil = int(akademik_yil)
    sonraki_yil = akademik_yil + 1
    donem = str(donem or "G")

    conn = None
    try:
        if not os.path.exists(db_path):
            return {"ok": False, "error": f"DB bulunamadi: {db_path}"}

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT ad FROM fakulte WHERE fakulte_id = ?", (fakulte_id,))
        fak = cur.fetchone()
        if not fak:
            return {"ok": False, "error": f"Fakulte bulunamadi: {fakulte_id}"}

        cur.execute(
            "SELECT bolum_id, ad FROM bolum WHERE fakulte_id = ? ORDER BY bolum_id",
            (fakulte_id,),
        )
        bolumler = [(int(r[0]), str(r[1] or "")) for r in cur.fetchall()]
        if not bolumler:
            return {"ok": False, "error": "Fakulteye ait bolum bulunamadi."}

        mevcut_mufredatlar = {}
        eksik_mufredat = []

        for bolum_id, bolum_adi in bolumler:
            cur.execute(
                """
                SELECT mufredat_id
                FROM mufredat
                WHERE fakulte_id = ? AND bolum_id = ? AND akademik_yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
                ORDER BY COALESCE(versiyon, 0) DESC, mufredat_id DESC
                LIMIT 1
                """,
                (fakulte_id, bolum_id, akademik_yil, donem),
            )
            row = cur.fetchone()
            if not row:
                eksik_mufredat.append({"bolum_id": bolum_id, "bolum": bolum_adi})
                continue

            mufredat_id = int(row[0])
            cur.execute(
                """
                SELECT d.ders_id
                FROM mufredat_ders md
                JOIN ders d ON d.ders_id = md.ders_id
                WHERE md.mufredat_id = ?
                ORDER BY md.ders_id
                """,
                (mufredat_id,),
            )
            dersler = [int(r[0]) for r in cur.fetchall()]
            if not dersler:
                eksik_mufredat.append({"bolum_id": bolum_id, "bolum": bolum_adi})
                continue
            mevcut_mufredatlar[bolum_id] = dersler

        if eksik_mufredat:
            return {
                "ok": False,
                "error": "Bazi bolumlerde secilen yil/donem icin mufredat bulunamadi.",
                "missing_curricula": eksik_mufredat,
            }

        eksik_kriter = []
        for bolum_id, dersler in mevcut_mufredatlar.items():
            bolum_adi = next((b[1] for b in bolumler if b[0] == bolum_id), str(bolum_id))
            for ders_id in dersler:
                if not _has_full_criteria(cur, ders_id, akademik_yil, donem):
                    cur.execute("SELECT ad FROM ders WHERE ders_id = ?", (ders_id,))
                    dr = cur.fetchone()
                    ders_adi = str(dr[0]) if dr else str(ders_id)
                    eksik_kriter.append(
                        {
                            "bolum_id": bolum_id,
                            "bolum": bolum_adi,
                            "ders_id": ders_id,
                            "ders": ders_adi,
                        }
                    )

        if eksik_kriter:
            return {
                "ok": False,
                "error": "Tum bolum mufredatlarinda kriterler tamamlanmadan otomatik gecis yapilamaz.",
                "missing_criteria": eksik_kriter,
            }

        tip_col = _resolve_elective_col(cur)

        if tip_col:
            cur.execute(
                f"""
                SELECT ders_id
                FROM ders
                WHERE fakulte_id = ?
                  AND COALESCE({tip_col}, '') LIKE 'Se%'
                """,
                (fakulte_id,),
            )
            aday_dersler = {int(r[0]) for r in cur.fetchall()}
        else:
            aday_dersler = set()

        for dersler in mevcut_mufredatlar.values():
            aday_dersler.update(int(d) for d in dersler)

        if not aday_dersler:
            return {
                "ok": False,
                "error": "Aday ders bulunamadi (fakulte dersi veya mufredat dersi yok).",
            }

        cur.execute(
            "SELECT ders_id, bolum_id, ad FROM ders WHERE fakulte_id = ?",
            (fakulte_id,),
        )
        ders_meta = {}
        for r in cur.fetchall():
            d_id = int(r[0])
            ders_meta[d_id] = {
                "bolum_id": int(r[1]) if r[1] is not None else None,
                "ad": str(r[2] or ""),
            }

        motor = KararMotoru()
        agirliklar = motor.ahp_calistir()

        metric_rows = []
        metric_map = {}
        for ders_id in sorted(aday_dersler):
            m = _read_course_metrics(cur, ders_id, akademik_yil, donem, motor)
            if ders_id in ders_meta:
                m["ders"] = ders_meta[ders_id].get("ad", str(ders_id))
            else:
                m["ders"] = str(ders_id)
            metric_rows.append(m)
            metric_map[ders_id] = m

        df = pd.DataFrame(metric_rows)
        if df.empty:
            return {"ok": False, "error": "Skor hesaplamak icin veri yok."}

        df_sonuc, _ = motor.topsis_calistir(df, agirliklar)
        skor_map = {}
        if not df_sonuc.empty:
            for _, r in df_sonuc.iterrows():
                d_id = int(r.get("ders_id", 0) or 0)
                if d_id <= 0:
                    continue
                kp = r.get("Kesinlesme_Puani")
                if kp is None or (isinstance(kp, float) and math.isnan(kp)):
                    kp = _safe_float2(r.get("AHP_TOPSIS_Skor"), 0.5) * 100.0
                skor_map[d_id] = round(_safe_float2(kp, 50.0), 2)

        cur.execute(
            """
            SELECT CAST(ders_id AS INTEGER) as d_id, statu, sayac
            FROM havuz
            WHERE yil = ? AND fakulte_id = ?
            """,
            (akademik_yil, fakulte_id),
        )
        prev_havuz = {
            int(r[0]): {"statu": int(r[1] or 0), "sayac": int(r[2] or 0)}
            for r in cur.fetchall()
            if r[0] is not None
        }

        bolum_sonuc = []
        yeni_mufredatlar = {}

        def _sort_key(d_id):
            sc = _safe_float2(skor_map.get(d_id), 0.0)
            bas = _safe_float2(metric_map.get(d_id, {}).get("basari"), 0.0)
            dol = _safe_float2(metric_map.get(d_id, {}).get("populerlik"), 0.0)
            return (sc, bas, dol, -int(d_id))

        tum_aday_sirali = sorted(list(aday_dersler), key=_sort_key, reverse=True)

        for bolum_id, bolum_adi in bolumler:
            mevcut = list(mevcut_mufredatlar.get(bolum_id, []))
            hedef_adet = len(mevcut)

            dusenler = []
            kalanlar = []

            for d_id in mevcut:
                score = _safe_float2(skor_map.get(d_id), 0.0)
                prev_statu = int(prev_havuz.get(d_id, {}).get("statu", 0))
                if prev_statu in (-1, -2) or score < float(drop_score_threshold):
                    dusenler.append(d_id)
                else:
                    kalanlar.append(d_id)

            if not dusenler:
                yeni = list(mevcut)
                eklenenler = []
            else:
                yeni = list(kalanlar)
                blok = set(yeni) | set(dusenler)

                bolum_ici = [
                    d_id
                    for d_id in tum_aday_sirali
                    if d_id not in blok
                    and int(prev_havuz.get(d_id, {}).get("statu", 0)) not in (-1, -2)
                    and ders_meta.get(d_id, {}).get("bolum_id") == bolum_id
                ]
                fakulte_geneli = [
                    d_id
                    for d_id in tum_aday_sirali
                    if d_id not in blok
                    and d_id not in bolum_ici
                    and int(prev_havuz.get(d_id, {}).get("statu", 0)) not in (-1, -2)
                ]

                for d_id in bolum_ici + fakulte_geneli:
                    if len(yeni) >= hedef_adet:
                        break
                    if d_id not in yeni:
                        yeni.append(d_id)

                eklenenler = [d for d in yeni if d not in mevcut]

                if len(yeni) < hedef_adet:
                    for d_id in sorted(dusenler, key=_sort_key, reverse=True):
                        if len(yeni) >= hedef_adet:
                            break
                        if d_id not in yeni:
                            yeni.append(d_id)

            yeni_unique = []
            seen = set()
            for d_id in yeni:
                if d_id not in seen:
                    seen.add(d_id)
                    yeni_unique.append(d_id)
            yeni_unique = yeni_unique[:hedef_adet]

            if len(yeni_unique) < hedef_adet:
                for d_id in mevcut:
                    if len(yeni_unique) >= hedef_adet:
                        break
                    if d_id not in yeni_unique:
                        yeni_unique.append(d_id)

            yeni_mufredatlar[bolum_id] = yeni_unique
            bolum_sonuc.append(
                {
                    "bolum_id": bolum_id,
                    "bolum": bolum_adi,
                    "mevcut_adet": len(mevcut),
                    "dusenler": [
                        {
                            "ders_id": d,
                            "ders": ders_meta.get(d, {}).get("ad", str(d)),
                            "score": _safe_float2(skor_map.get(d), 0.0),
                        }
                        for d in dusenler
                    ],
                    "eklenenler": [
                        {
                            "ders_id": d,
                            "ders": ders_meta.get(d, {}).get("ad", str(d)),
                            "score": _safe_float2(skor_map.get(d), 0.0),
                        }
                        for d in eklenenler
                    ],
                    "tasindi_mi": len(dusenler) == 0,
                }
            )

        for bolum_id, bolum_adi in bolumler:
            dersler = yeni_mufredatlar.get(bolum_id, [])
            cur.execute(
                """
                SELECT mufredat_id
                FROM mufredat
                WHERE fakulte_id = ? AND bolum_id = ? AND akademik_yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
                ORDER BY COALESCE(versiyon, 0) DESC, mufredat_id DESC
                LIMIT 1
                """,
                (fakulte_id, bolum_id, sonraki_yil, donem),
            )
            existing = cur.fetchone()
            if existing:
                hedef_muf_id = int(existing[0])
                cur.execute("DELETE FROM mufredat_ders WHERE mufredat_id = ?", (hedef_muf_id,))
                cur.execute(
                    "UPDATE mufredat SET durum = ? WHERE mufredat_id = ?",
                    ("Otomatik", hedef_muf_id),
                )
            else:
                cur.execute(
                    "SELECT COALESCE(MAX(versiyon), 0) FROM mufredat WHERE fakulte_id = ? AND bolum_id = ?",
                    (fakulte_id, bolum_id),
                )
                max_ver = int(cur.fetchone()[0] or 0)
                cur.execute(
                    """
                    INSERT INTO mufredat (fakulte_id, bolum_id, akademik_yil, donem, durum, versiyon)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (fakulte_id, bolum_id, sonraki_yil, donem, "Otomatik", max_ver + 1),
                )
                hedef_muf_id = int(cur.lastrowid)

            for d_id in dersler:
                cur.execute(
                    "INSERT OR IGNORE INTO mufredat_ders (mufredat_id, ders_id) VALUES (?, ?)",
                    (hedef_muf_id, int(d_id)),
                )

        secilenler = set()
        for dersler in yeni_mufredatlar.values():
            secilenler.update(int(d) for d in dersler)

        cur.execute("SELECT ders_id, bolum_id, ad FROM ders WHERE fakulte_id = ?", (fakulte_id,))
        tum_dersler = [(int(r[0]), int(r[1]) if r[1] is not None else None, str(r[2] or "")) for r in cur.fetchall()]

        upsert_count = 0
        for ders_id, bolum_id, ders_adi in tum_dersler:
            prev = prev_havuz.get(ders_id, {"statu": 0, "sayac": 0})
            yeni_statu, yeni_sayac = calculate_next_status(
                int(prev.get("statu", 0)),
                int(prev.get("sayac", 0)),
                ders_id in secilenler,
            )
            skor_val = int(round(_safe_float2(skor_map.get(ders_id), 50.0)))

            cur.execute(
                """
                UPDATE havuz SET bolum_id=?, statu=?, sayac=?, skor=?, ders_adi=?
                WHERE ders_id=? AND fakulte_id=? AND yil=?
                """,
                (bolum_id, yeni_statu, yeni_sayac, skor_val, ders_adi or "", str(ders_id), fakulte_id, sonraki_yil),
            )
            if cur.rowcount == 0:
                cur.execute(
                    """
                    INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, statu, sayac, skor, ders_adi)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (str(ders_id), sonraki_yil, fakulte_id, bolum_id, yeni_statu, yeni_sayac, skor_val, ders_adi or ""),
                )
            upsert_count += 1

        conn.commit()

        return {
            "ok": True,
            "fakulte_id": fakulte_id,
            "fakulte": str(fak[0]),
            "year_from": akademik_yil,
            "year_to": sonraki_yil,
            "donem": donem,
            "departments": bolum_sonuc,
            "pool_rows_upserted": upsert_count,
        }

    except Exception as exc:
        if conn:
            conn.rollback()
        return {
            "ok": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    run_automatic_scoring()