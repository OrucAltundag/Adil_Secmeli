# -*- coding: utf-8 -*-
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
import logging
from app.services.havuz_karar import calculate_next_status

logger = logging.getLogger(__name__)

# ---------- BÖLÜM 1: Karar Motoru (AHP + TOPSIS) ----------
# AHP için RI (Random Index) - 4 kriter için
RI_4 = 0.90
DROP_SCORE_THRESHOLD = 40.0
DROP_AVERAGE_GRADE_THRESHOLD = 45.0

# Mufredat disi (havuz) dersler: merkez 50, yalnizca anket ile ±10 sapma (40-60).
POOL_DEFAULT_SCORE = 50.0
POOL_ANKET_SCORE_SPREAD = 10.0

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

    cursor.execute("SELECT bolum_id, ad, fakulte_id FROM bolum")
    db_bolumler = {
        str(r[1]).lower().strip(): {"bolum_id": int(r[0]), "fakulte_id": int(r[2])}
        for r in cursor.fetchall()
    }

    cursor.execute("SELECT ders_id, ad FROM ders")
    db_dersler = {str(r[1]).lower().strip(): int(r[0]) for r in cursor.fetchall()}

    col_bolum = "bölüm"
    ders_cols = [f"seçmeli ders {i}" for i in range(1, 6)]
    count_ders = 0

    for _, row in df.iterrows():
        bolum_adi = str(row.get(col_bolum, "") or "").strip()
        if not bolum_adi:
            continue

        bolum_id = None
        bolum_fakulte_id = None
        bolum_adi_low = bolum_adi.lower()
        for k, info in db_bolumler.items():
            if k in bolum_adi_low or bolum_adi_low in k:
                bolum_id = int(info["bolum_id"])
                bolum_fakulte_id = int(info["fakulte_id"])
                break
        if not bolum_id or bolum_fakulte_id is None:
            continue

        cursor.execute(
            "INSERT INTO mufredat (fakulte_id, bolum_id, akademik_yil, donem, durum) VALUES (?, ?, 2022, 'Güz', 'Resmi')",
            (bolum_fakulte_id, bolum_id)
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
                    (d_id, bolum_fakulte_id)
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
    """
    Acilis veya manuel tetikleme: base_year sonrasi mufredati sifirlar,
    kriterleri hazir fakulte/yillar icin zincirleme sonraki yil uretir,
    sonucu curriculum_generation_log tablosuna yazar.
    """
    return rebuild_school_curricula(
        db_path=db_path,
        base_year=2022,
        donem="G",
        max_rounds=8,
    )



def _normalize_mufredat_faculty_ids(cur):
    """
    Legacy veri setlerinde mufredat.fakulte_id yanlis yazilmis olabiliyor.
    bolum tablosunu kaynak kabul ederek bu alanı normalize eder.
    """
    try:
        cur.execute(
            """
            UPDATE mufredat
            SET fakulte_id = (
                SELECT b.fakulte_id
                FROM bolum b
                WHERE b.bolum_id = mufredat.bolum_id
                LIMIT 1
            )
            WHERE EXISTS (
                SELECT 1
                FROM bolum b2
                WHERE b2.bolum_id = mufredat.bolum_id
            )
              AND COALESCE(fakulte_id, -1) <> COALESCE((
                SELECT b3.fakulte_id
                FROM bolum b3
                WHERE b3.bolum_id = mufredat.bolum_id
                LIMIT 1
              ), -1)
            """
        )
        return int(cur.rowcount or 0)
    except Exception:
        return 0


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


def _has_generation_criteria(cur, ders_id, yil, donem):
    """
    Yeni yil mufredat uretimi icin zorunlu kriter kontrolu.
    Sadece ders_kriterleri kaydini kabul eder; performans/pop fallback'i kullanmaz.
    """
    try:
        cur.execute(
            """
            SELECT toplam_ogrenci, gecen_ogrenci, basari_ortalamasi, kontenjan, kayitli_ogrenci
            FROM ders_kriterleri
            WHERE ders_id = ? AND yil = ?
              AND (COALESCE(TRIM(donem), '') = '' OR LOWER(SUBSTR(TRIM(donem), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1)))
            ORDER BY CASE
                WHEN LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1)) THEN 0
                ELSE 1
            END, id DESC
            LIMIT 1
            """,
            (int(ders_id), int(yil), str(donem), str(donem)),
        )
        row = cur.fetchone()
        if not row:
            return False

        toplam = _safe_float2(row[0], 0.0)
        gecen = _safe_float2(row[1], 0.0)
        ortalama_not = _safe_float2(row[2], 0.0)
        kontenjan = _safe_float2(row[3], 0.0)
        kayitli = _safe_float2(row[4], 0.0)

        return toplam > 0 and kontenjan > 0 and gecen >= 0 and kayitli >= 0 and ortalama_not > 0
    except Exception:
        return False


def _has_full_criteria(cur, ders_id, yil, donem):
    try:
        ders_id = int(ders_id)
        yil = int(yil)
        cur.execute(
            """
            SELECT toplam_ogrenci, gecen_ogrenci, basari_ortalamasi, kontenjan, kayitli_ogrenci
            FROM ders_kriterleri
            WHERE ders_id = ? AND yil = ?
              AND (COALESCE(TRIM(donem), '') = '' OR LOWER(SUBSTR(TRIM(donem), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1)))
            ORDER BY CASE WHEN LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1)) THEN 0 ELSE 1 END, id DESC
            LIMIT 1
            """,
            (ders_id, yil, str(donem), str(donem)),
        )
        row = cur.fetchone()

        if row:
            toplam = _safe_float2(row[0], 0.0)
            gecen = _safe_float2(row[1], 0.0)
            ortalama_not = _safe_float2(row[2], 0.0)
            kontenjan = _safe_float2(row[3], 0.0)
            kayitli = _safe_float2(row[4], 0.0)
            if ortalama_not <= 0:
                cur.execute(
                    """
                    SELECT ortalama_not
                    FROM performans
                    WHERE ders_id = ? AND akademik_yil = ?
                    ORDER BY pfrs_id DESC
                    LIMIT 1
                    """,
                    (ders_id, yil),
                )
                pf = cur.fetchone()
                ortalama_not = _safe_float2(pf[0] if pf else None, 0.0)

            if toplam > 0 and kontenjan > 0 and gecen >= 0 and kayitli >= 0 and ortalama_not > 0:
                return True

        # Fallback: kriter satiri eksik/parsiyel olsa bile performans + populerlik
        # verisi varsa dersi "hesaplanabilir" kabul et.
        cur.execute(
            """
            SELECT ortalama_not, basari_orani
            FROM performans
            WHERE ders_id = ? AND akademik_yil = ?
            ORDER BY pfrs_id DESC
            LIMIT 1
            """,
            (ders_id, yil),
        )
        pf = cur.fetchone()

        try:
            cur.execute(
                """
                SELECT kontenjan, doluluk_orani
                FROM populerlik
                WHERE ders_id = ? AND akademik_yil = ?
                ORDER BY pop_id DESC
                LIMIT 1
                """,
                (ders_id, yil),
            )
        except sqlite3.OperationalError:
            cur.execute(
                """
                SELECT NULL as kontenjan, doluluk_orani
                FROM populerlik
                WHERE ders_id = ? AND akademik_yil = ?
                ORDER BY rowid DESC
                LIMIT 1
                """,
                (ders_id, yil),
            )
        pop = cur.fetchone()

        ortalama_not = _safe_float2(pf[0] if pf else None, 0.0)
        basari_orani = _safe_float2(pf[1] if pf else None, -1.0)
        kontenjan = _safe_float2(pop[0] if pop else None, 0.0)
        doluluk = _safe_float2(pop[1] if pop else None, -1.0)

        perf_ok = ortalama_not > 0 and basari_orani >= 0
        pop_ok = kontenjan > 0 or doluluk >= 0
        return perf_ok and pop_ok
    except Exception:
        return False


def _read_course_metrics(cur, ders_id, yil, donem, motor):
    try:
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
    except sqlite3.OperationalError:
        cur.execute(
            """
            SELECT toplam_ogrenci, gecen_ogrenci, basari_ortalamasi,
                   kontenjan, kayitli_ogrenci
            FROM ders_kriterleri
            WHERE ders_id = ? AND yil = ?
              AND (COALESCE(TRIM(donem), '') = '' OR LOWER(SUBSTR(TRIM(donem), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1)))
            ORDER BY id DESC
            LIMIT 1
            """,
            (int(ders_id), int(yil), str(donem)),
        )
        row = cur.fetchone()
        dk = (row[0], row[1], row[2], row[3], row[4], 0, 0) if row else None

    try:
        cur.execute(
            """
            SELECT ortalama_not, basari_orani
            FROM performans
            WHERE ders_id = ? AND akademik_yil = ?
            ORDER BY pfrs_id DESC
            LIMIT 1
            """,
            (int(ders_id), int(yil)),
        )
    except sqlite3.OperationalError:
        cur.execute(
            """
            SELECT ortalama_not, basari_orani
            FROM performans
            WHERE ders_id = ? AND akademik_yil = ?
            ORDER BY rowid DESC
            LIMIT 1
            """,
            (int(ders_id), int(yil)),
        )
    pf = cur.fetchone()

    try:
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
    except sqlite3.OperationalError:
        cur.execute(
            """
            SELECT doluluk_orani
            FROM populerlik
            WHERE ders_id = ? AND akademik_yil = ?
            ORDER BY rowid DESC
            LIMIT 1
            """,
            (int(ders_id), int(yil)),
        )
    pop = cur.fetchone()

    ortalama_not = _safe_float2(pf[0] if pf else None, 0.0)
    basari = _safe_float2(pf[1] if pf else None, 0.0)
    doluluk = _safe_float2(pop[0] if pop else None, 0.0)
    anket = 0.5

    if dk:
        toplam = _safe_float2(dk[0], 0.0)
        gecen = _safe_float2(dk[1], 0.0)
        ortalama_not = _safe_float2(dk[2], ortalama_not)
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
        "ortalama_not": max(0.0, min(100.0, _safe_float2(ortalama_not, 0.0))),
    }


def evaluate_drop_reasons(
    score_100,
    average_grade,
    score_threshold=DROP_SCORE_THRESHOLD,
    average_grade_threshold=DROP_AVERAGE_GRADE_THRESHOLD,
):
    reasons = []
    if _safe_float2(score_100, 0.0) < float(score_threshold):
        reasons.append(f"Kesinlesme puani {float(score_threshold):.0f} altinda")
    if _safe_float2(average_grade, 0.0) < float(average_grade_threshold):
        reasons.append(f"Gecme not ortalamasi {float(average_grade_threshold):.0f} altinda")
    return reasons


def should_drop_course(
    score_100,
    average_grade,
    score_threshold=DROP_SCORE_THRESHOLD,
    average_grade_threshold=DROP_AVERAGE_GRADE_THRESHOLD,
):
    reasons = evaluate_drop_reasons(
        score_100,
        average_grade,
        score_threshold=score_threshold,
        average_grade_threshold=average_grade_threshold,
    )
    return len(reasons) > 0, reasons


def _pool_course_score_anket_only(anket):
    """
    Mufredat disi dersler icin kesinlesme puani. TOPSIS'e girmez.
    score = 50 + (anket - 0.5) * 2 * 10  => anket 0.5 -> 50, 1.0 -> 60, 0.0 -> 40.
    None/bos/gecersiz -> anket 0.5 (50). Dis aralik [0,1] disina clamp.
    """
    if anket is None:
        ratio = 0.5
    else:
        try:
            ratio = float(anket)
            if math.isnan(ratio) or math.isinf(ratio):
                ratio = 0.5
        except (TypeError, ValueError):
            ratio = 0.5
    ratio = max(0.0, min(1.0, ratio))
    return POOL_DEFAULT_SCORE + (ratio - 0.5) * 2.0 * POOL_ANKET_SCORE_SPREAD


def get_faculty_year_topsis_results(cur, fakulte_id, akademik_yil, donem="G", include_course_ids=None):
    fakulte_id = int(fakulte_id)
    akademik_yil = int(akademik_yil)
    donem = str(donem or "G")
    include_course_ids = {int(d) for d in (include_course_ids or [])}

    cur.execute("PRAGMA table_info(ders)")
    ders_cols = {str(r[1]) for r in cur.fetchall()}
    has_fakulte_col = "fakulte_id" in ders_cols
    has_bolum_col = "bolum_id" in ders_cols
    base_where = "WHERE fakulte_id = ?" if has_fakulte_col else "WHERE 1=1"
    base_params = (fakulte_id,) if has_fakulte_col else tuple()

    tip_col = _resolve_elective_col(cur)
    aday_dersler = set()
    if tip_col:
        cur.execute(
            f"""
            SELECT ders_id
            FROM ders
            {base_where}
              AND (
                    COALESCE({tip_col}, '') LIKE 'Se%'
                 OR LOWER(COALESCE({tip_col}, '')) LIKE '%secmeli%'
                 OR LOWER(COALESCE({tip_col}, '')) LIKE '%seçmeli%'
              )
            """,
            base_params,
        )
        aday_dersler.update(int(r[0]) for r in cur.fetchall())
    else:
        cur.execute(
            f"SELECT ders_id FROM ders {base_where}",
            base_params,
        )
        aday_dersler.update(int(r[0]) for r in cur.fetchall())

    # Mufredattaki dersler (bolum veya legacy m.fakulte_id yolu — _get_curriculum_course_ids)
    aday_dersler.update(_get_curriculum_course_ids(cur, fakulte_id, akademik_yil, donem))
    aday_dersler.update(include_course_ids)

    if not aday_dersler:
        return {
            "ok": False,
            "error": "Aday ders bulunamadi (fakulte ve yil icin TOPSIS evreni bos).",
            "scores": {},
            "metric_map": {},
            "ders_meta": {},
        }

    ders_meta = {}
    meta_ids = sorted(int(d) for d in aday_dersler)
    if meta_ids:
        chunk_size = 900  # SQLite degisken limitine takilmamak icin.
        for i in range(0, len(meta_ids), chunk_size):
            chunk = meta_ids[i : i + chunk_size]
            placeholders = ",".join("?" for _ in chunk)
            cur.execute(
                f"""
                SELECT ders_id, {'bolum_id' if has_bolum_col else 'NULL as bolum_id'}, ad
                FROM ders
                WHERE ders_id IN ({placeholders})
                """,
                tuple(chunk),
            )
            for r in cur.fetchall():
                d_id = int(r[0])
                ders_meta[d_id] = {
                    "bolum_id": int(r[1]) if r[1] is not None else None,
                    "ad": str(r[2] or ""),
                }

    motor = KararMotoru()
    agirliklar = motor.ahp_calistir()
    metric_map = {}
    for ders_id in sorted(aday_dersler):
        m = _read_course_metrics(cur, ders_id, akademik_yil, donem, motor)
        m["ders"] = ders_meta.get(ders_id, {}).get("ad", str(ders_id))
        metric_map[ders_id] = m

    curriculum_course_ids = _get_curriculum_course_ids(
        cur=cur, fakulte_id=fakulte_id, akademik_yil=akademik_yil, donem=donem
    )
    curriculum_courses = sorted(d for d in aday_dersler if d in curriculum_course_ids)
    pool_courses = sorted(d for d in aday_dersler if d not in curriculum_course_ids)

    skor_map = {}
    df_sonuc = pd.DataFrame()
    meta = {}

    # Mufredattaki dersler: sadece bunlar TOPSIS pipeline'ina girer.
    if curriculum_courses:
        df_cur = pd.DataFrame([metric_map[cid] for cid in curriculum_courses])
        if not df_cur.empty:
            df_sonuc, meta = motor.topsis_calistir(df_cur, agirliklar)
            if not df_sonuc.empty:
                for _, r in df_sonuc.iterrows():
                    d_id = int(r.get("ders_id", 0) or 0)
                    if d_id <= 0:
                        continue
                    kp = r.get("Kesinlesme_Puani")
                    if kp is None or (isinstance(kp, float) and math.isnan(kp)):
                        kp = _safe_float2(r.get("AHP_TOPSIS_Skor"), 0.0) * 100.0
                    skor_map[d_id] = round(_safe_float2(kp, 0.0), 2)
    else:
        # Fallback: bu fakulte+yil icin mufredatta hic aday ders yok; TOPSIS calismaz,
        # tum adaylar havuz mantigi (anket-only) ile puanlanir.
        logger.debug(
            "get_faculty_year_topsis_results: TOPSIS evreni bos (mufredatta aday yok); "
            "fakulte_id=%s yil=%s, pool_only=%s ders",
            fakulte_id,
            akademik_yil,
            len(pool_courses),
        )

    # Mufredat disi: TOPSIS'e hic girmez; yalnizca anket ile 50±10.
    for d_id in pool_courses:
        anket_val = (metric_map.get(d_id) or {}).get("anket")
        skor_map[d_id] = round(_pool_course_score_anket_only(anket_val), 2)

    logger.debug(
        "get_faculty_year_topsis_results: TOPSIS=%s ders, pool_anket=%s ders (fakulte_id=%s yil=%s)",
        len(curriculum_courses),
        len(pool_courses),
        fakulte_id,
        akademik_yil,
    )

    if not skor_map:
        return {
            "ok": False,
            "error": "Hicbir ders icin skor uretilemedi.",
            "scores": {},
            "metric_map": metric_map,
            "ders_meta": ders_meta,
        }

    return {
        "ok": True,
        "scores": skor_map,
        "metric_map": metric_map,
        "ders_meta": ders_meta,
        "df_sonuc": df_sonuc,
        "meta": meta,
    }


def _get_curriculum_course_ids(cur, fakulte_id, akademik_yil, donem="G"):
    """
    Fakulte + yil (+ donem ilk harf) icin mufredatta bulunan ders_id kumesini dondurur.
    Once bolum uzerinden (canonical); basarisizsa mufredat.fakulte_id (legacy sema).
    """
    fakulte_id = int(fakulte_id)
    akademik_yil = int(akademik_yil)
    donem = str(donem or "G")

    def _fetch_via_bolum(with_donem: bool):
        if with_donem:
            cur.execute(
                """
                SELECT DISTINCT md.ders_id
                FROM mufredat m
                JOIN bolum b ON b.bolum_id = m.bolum_id
                JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
                WHERE b.fakulte_id = ? AND m.akademik_yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
                """,
                (fakulte_id, akademik_yil, donem),
            )
        else:
            cur.execute(
                """
                SELECT DISTINCT md.ders_id
                FROM mufredat m
                JOIN bolum b ON b.bolum_id = m.bolum_id
                JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
                WHERE b.fakulte_id = ? AND m.akademik_yil = ?
                """,
                (fakulte_id, akademik_yil),
            )
        return {int(r[0]) for r in cur.fetchall() if r and r[0] is not None}

    def _fetch_via_mufredat_fakulte(with_donem: bool):
        if with_donem:
            cur.execute(
                """
                SELECT DISTINCT md.ders_id
                FROM mufredat m
                JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
                WHERE m.fakulte_id = ? AND m.akademik_yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
                """,
                (fakulte_id, akademik_yil, donem),
            )
        else:
            cur.execute(
                """
                SELECT DISTINCT md.ders_id
                FROM mufredat m
                JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
                WHERE m.fakulte_id = ? AND m.akademik_yil = ?
                """,
                (fakulte_id, akademik_yil),
            )
        return {int(r[0]) for r in cur.fetchall() if r and r[0] is not None}

    try:
        return _fetch_via_bolum(True)
    except sqlite3.OperationalError:
        try:
            return _fetch_via_bolum(False)
        except sqlite3.OperationalError:
            try:
                return _fetch_via_mufredat_fakulte(True)
            except sqlite3.OperationalError:
                try:
                    return _fetch_via_mufredat_fakulte(False)
                except sqlite3.OperationalError:
                    logger.debug(
                        "_get_curriculum_course_ids: mufredat sorgusu basarisiz fakulte_id=%s yil=%s",
                        fakulte_id,
                        akademik_yil,
                    )
                    return set()


def persist_faculty_year_topsis_scores(cur, fakulte_id, akademik_yil, skor_map, ders_meta, donem="G"):
    fakulte_id = int(fakulte_id)
    akademik_yil = int(akademik_yil)
    active_curriculum_ids = _get_curriculum_course_ids(
        cur=cur,
        fakulte_id=fakulte_id,
        akademik_yil=akademik_yil,
        donem=donem,
    )
    cur.execute(
        "UPDATE havuz SET skor = NULL WHERE fakulte_id = ? AND yil = ?",
        (fakulte_id, akademik_yil),
    )

    upsert_count = 0
    for ders_id, score in skor_map.items():
        meta = ders_meta.get(int(ders_id), {})
        bolum_id = meta.get("bolum_id")
        ders_adi = str(meta.get("ad") or "")
        score_val = round(_safe_float2(score, 0.0), 2)

        cur.execute(
            """
            UPDATE havuz
            SET bolum_id = COALESCE(?, bolum_id),
                ders_adi = CASE WHEN ? <> '' THEN ? ELSE ders_adi END,
                skor = ?
            WHERE ders_id = ? AND fakulte_id = ? AND yil = ?
            """,
            (bolum_id, ders_adi, ders_adi, score_val, str(ders_id), fakulte_id, akademik_yil),
        )
        if cur.rowcount == 0:
            init_statu = 1 if int(ders_id) in active_curriculum_ids else 0
            cur.execute(
                """
                INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, statu, sayac, skor, ders_adi)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (str(ders_id), akademik_yil, fakulte_id, bolum_id, init_statu, score_val, ders_adi),
            )
        upsert_count += 1
    return upsert_count


def ensure_pool_visibility_for_curriculum(cur, fakulte_id, akademik_yil, donem="G"):
    """
    Havuz ekraninda gorunurluk ve kural tutarliligi icin:
    - Mufredatta bulunan dersler havuzda mutlaka satira sahip olur.
    - Mufredatta olan derslerin statu degeri 1'e hizalanir.
    """
    fakulte_id = int(fakulte_id)
    akademik_yil = int(akademik_yil)
    curriculum_ids = sorted(
        _get_curriculum_course_ids(
            cur=cur,
            fakulte_id=fakulte_id,
            akademik_yil=akademik_yil,
            donem=donem,
        )
    )
    if not curriculum_ids:
        return {"updated": 0, "inserted": 0, "curriculum_count": 0}

    updated = 0
    inserted = 0
    chunk_size = 900
    for i in range(0, len(curriculum_ids), chunk_size):
        chunk = curriculum_ids[i : i + chunk_size]
        placeholders = ",".join("?" for _ in chunk)

        cur.execute(
            f"""
            UPDATE havuz
            SET statu = 1
            WHERE fakulte_id = ? AND yil = ?
              AND CAST(ders_id AS INTEGER) IN ({placeholders})
            """,
            (fakulte_id, akademik_yil, *chunk),
        )
        updated += int(cur.rowcount or 0)

        cur.execute(
            f"""
            SELECT d.ders_id, d.bolum_id, d.ad
            FROM ders d
            WHERE d.ders_id IN ({placeholders})
              AND NOT EXISTS (
                    SELECT 1
                    FROM havuz h
                    WHERE h.fakulte_id = ? AND h.yil = ?
                      AND CAST(h.ders_id AS INTEGER) = d.ders_id
              )
            """,
            (*chunk, fakulte_id, akademik_yil),
        )
        eksikler = cur.fetchall()
        for r in eksikler:
            if not r or r[0] is None:
                continue
            cur.execute(
                """
                INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, statu, sayac, skor, ders_adi)
                VALUES (?, ?, ?, ?, 1, 0, NULL, ?)
                """,
                (
                    str(int(r[0])),
                    akademik_yil,
                    fakulte_id,
                    int(r[1]) if r[1] is not None else None,
                    str(r[2] or ""),
                ),
            )
            inserted += 1

    return {
        "updated": updated,
        "inserted": inserted,
        "curriculum_count": len(curriculum_ids),
    }


def generate_next_year_curricula(
    db_path="data/adil_secmeli.db",
    fakulte_id=None,
    akademik_yil=None,
    donem="G",
    drop_score_threshold=DROP_SCORE_THRESHOLD,
    drop_average_grade_threshold=DROP_AVERAGE_GRADE_THRESHOLD,
):
    """
    Faculty + year + term icin bolum bazli sonraki yil mufredati olusturur.
    - Validasyon: Sadece mufredatta olan derslerin zorunlu kriterleri; anket zorunlu degil.
    - Havuz / mufredat disi dersler validasyonu bloklamaz.
    - Dusen dersler (skor baraj altinda veya ortalama not baraji altinda)
      yerine kesinlesme puani en yuksek adaylar eklenir.
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
        normalized_rows = _normalize_mufredat_faculty_ids(cur)

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
                SELECT m.mufredat_id
                FROM mufredat m
                JOIN bolum b ON b.bolum_id = m.bolum_id
                WHERE b.fakulte_id = ? AND m.bolum_id = ? AND m.akademik_yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
                ORDER BY COALESCE(m.versiyon, 0) DESC, m.mufredat_id DESC
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
        prev_curriculum_ids = set()
        for dersler in mevcut_mufredatlar.values():
            prev_curriculum_ids.update(int(d) for d in dersler)

        def _effective_prev_state(ders_id: int):
            raw = prev_havuz.get(int(ders_id))
            raw_statu = int(raw.get("statu", 0)) if raw else None
            raw_sayac = int(raw.get("sayac", 0)) if raw else 0

            # Kaynak yil mufredatinda olan ders "aktif" kabul edilir.
            # Legacy/veri kaymasi nedeniyle havuzda 0/-1 görünse bile kurala hizalar.
            if int(ders_id) in prev_curriculum_ids and raw_statu != 1:
                return 1, raw_sayac
            if raw_statu is None:
                return 0, 0
            return raw_statu, raw_sayac

        eksik_kriter = []
        for bolum_id, dersler in mevcut_mufredatlar.items():
            bolum_adi = next((b[1] for b in bolumler if b[0] == bolum_id), str(bolum_id))
            for ders_id in dersler:
                prev_statu, _ = _effective_prev_state(ders_id)
                if prev_statu != 1:
                    continue
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
            logger.warning(
                "generate_next_year_curricula: %d ders icin kriter eksik (fakulte_id=%s yil=%s). "
                "Bu dersler varsayilan degerlerle hesaplanacak.",
                len(eksik_kriter), fakulte_id, akademik_yil,
            )

        score_pack = get_faculty_year_topsis_results(
            cur=cur,
            fakulte_id=fakulte_id,
            akademik_yil=akademik_yil,
            donem=donem,
        )
        if not score_pack.get("ok"):
            return {
                "ok": False,
                "error": score_pack.get("error", "TOPSIS skorlari olusturulamadi."),
            }

        skor_map = dict(score_pack.get("scores", {}))
        metric_map = dict(score_pack.get("metric_map", {}))
        ders_meta = dict(score_pack.get("ders_meta", {}))
        aday_dersler = set(int(d) for d in metric_map.keys())
        if not aday_dersler:
            return {"ok": False, "error": "Skor hesaplamak icin aday ders bulunamadi."}

        year_score_upserts = persist_faculty_year_topsis_scores(
            cur=cur,
            fakulte_id=fakulte_id,
            akademik_yil=akademik_yil,
            skor_map=skor_map,
            ders_meta=ders_meta,
            donem=donem,
        )

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
            drop_reason_map = {}
            drop_avg_map = {}

            for d_id in mevcut:
                score = _safe_float2(skor_map.get(d_id), 0.0)
                ortalama_not = _safe_float2(metric_map.get(d_id, {}).get("ortalama_not"), 0.0)
                prev_statu, _ = _effective_prev_state(d_id)
                drop_reasons = evaluate_drop_reasons(
                    score_100=score,
                    average_grade=ortalama_not,
                    score_threshold=drop_score_threshold,
                    average_grade_threshold=drop_average_grade_threshold,
                )
                if prev_statu in (-1, -2):
                    drop_reasons = ["Gecmis statu nedeniyle secilemez"] + drop_reasons
                if prev_statu in (-1, -2) or drop_reasons:
                    dusenler.append(d_id)
                    drop_reason_map[d_id] = drop_reasons
                    drop_avg_map[d_id] = ortalama_not
                else:
                    kalanlar.append(d_id)

            if not dusenler:
                yeni = list(mevcut)
                eklenenler = []
                ekleme_nedenleri = {}
            else:
                yeni = list(kalanlar)
                blok = set(yeni) | set(dusenler)
                ekleme_nedenleri = {}

                bolum_ici = [
                    d_id
                    for d_id in tum_aday_sirali
                    if d_id not in blok
                    and _effective_prev_state(d_id)[0] not in (-1, -2)
                    and ders_meta.get(d_id, {}).get("bolum_id") == bolum_id
                ]
                fakulte_geneli = [
                    d_id
                    for d_id in tum_aday_sirali
                    if d_id not in blok
                    and d_id not in bolum_ici
                    and _effective_prev_state(d_id)[0] not in (-1, -2)
                ]

                for d_id in bolum_ici + fakulte_geneli:
                    if len(yeni) >= hedef_adet:
                        break
                    if d_id not in yeni:
                        yeni.append(d_id)
                        if d_id in bolum_ici:
                            ekleme_nedenleri[d_id] = ["Bolum ici en yuksek aday"]
                        else:
                            ekleme_nedenleri[d_id] = ["Fakulte geneli en yuksek aday"]

                eklenenler = [d for d in yeni if d not in mevcut]

                if len(yeni) < hedef_adet:
                    for d_id in sorted(dusenler, key=_sort_key, reverse=True):
                        if len(yeni) >= hedef_adet:
                            break
                        if d_id not in yeni:
                            yeni.append(d_id)
                            ekleme_nedenleri[d_id] = ["Kontenjan korunumu icin geri eklendi"]

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
                            "average_grade": _safe_float2(drop_avg_map.get(d), 0.0),
                            "reasons": drop_reason_map.get(d, []),
                        }
                        for d in dusenler
                    ],
                    "eklenenler": [
                        {
                            "ders_id": d,
                            "ders": ders_meta.get(d, {}).get("ad", str(d)),
                            "score": _safe_float2(skor_map.get(d), 0.0),
                            "reasons": ekleme_nedenleri.get(d, ["Yuksek kesinlesme puani"]),
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
                SELECT m.mufredat_id
                FROM mufredat m
                JOIN bolum b ON b.bolum_id = m.bolum_id
                WHERE b.fakulte_id = ? AND m.bolum_id = ? AND m.akademik_yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
                ORDER BY COALESCE(m.versiyon, 0) DESC, m.mufredat_id DESC
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
                    "SELECT COALESCE(MAX(versiyon), 0) FROM mufredat WHERE bolum_id = ?",
                    (bolum_id,),
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

        cur.execute(
            """
            SELECT DISTINCT d.ders_id, d.bolum_id, d.ad
            FROM ders d
            LEFT JOIN bolum b ON b.bolum_id = d.bolum_id
            WHERE d.fakulte_id = ? OR b.fakulte_id = ?
            """,
            (fakulte_id, fakulte_id),
        )
        tum_ders_map = {
            int(r[0]): (
                int(r[1]) if r[1] is not None else None,
                str(r[2] or ""),
            )
            for r in cur.fetchall()
            if r and r[0] is not None
        }

        gerekli_idler = set(int(k) for k in prev_havuz.keys()) | set(int(k) for k in secilenler) | set(
            int(k) for k in prev_curriculum_ids
        )
        eksik_meta_ids = sorted(d for d in gerekli_idler if d not in tum_ders_map)
        if eksik_meta_ids:
            chunk_size = 900  # SQLite degisken limitine takilmamak icin.
            for i in range(0, len(eksik_meta_ids), chunk_size):
                chunk = eksik_meta_ids[i : i + chunk_size]
                placeholders = ",".join("?" for _ in chunk)
                cur.execute(
                    f"""
                    SELECT ders_id, bolum_id, ad
                    FROM ders
                    WHERE ders_id IN ({placeholders})
                    """,
                    tuple(chunk),
                )
                for r in cur.fetchall():
                    if not r or r[0] is None:
                        continue
                    tum_ders_map[int(r[0])] = (
                        int(r[1]) if r[1] is not None else None,
                        str(r[2] or ""),
                    )

        tum_dersler = [
            (int(d_id), meta[0], meta[1])
            for d_id, meta in sorted(tum_ders_map.items(), key=lambda x: x[0])
        ]

        upsert_count = 0
        for ders_id, bolum_id, ders_adi in tum_dersler:
            eff_statu, eff_sayac = _effective_prev_state(ders_id)
            yeni_statu, yeni_sayac = calculate_next_status(
                int(eff_statu),
                int(eff_sayac),
                ders_id in secilenler,
            )
            skor_val = None

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
            "missing_curricula": eksik_mufredat,
            "pool_rows_upserted": upsert_count,
            "year_score_upserted": year_score_upserts,
            "normalized_curricula": normalized_rows,
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


def auto_generate_next_year_curricula(db_path="data/adil_secmeli.db", donem="G"):
    summary = {
        "ok": True,
        "generated": [],
        "skipped": [],
        "errors": [],
    }
    if not os.path.exists(db_path):
        summary["ok"] = False
        summary["errors"].append({"error": f"DB bulunamadi: {db_path}"})
        return summary

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    _normalize_mufredat_faculty_ids(cur)
    conn.commit()
    cur.execute("SELECT fakulte_id, ad FROM fakulte ORDER BY fakulte_id")
    faculties = [(int(r[0]), str(r[1] or "")) for r in cur.fetchall()]
    conn.close()

    def _find_candidate_year(cur, fakulte_id, donem):
        cur.execute(
            """
            SELECT DISTINCT m.akademik_yil
            FROM mufredat m
            JOIN bolum b ON b.bolum_id = m.bolum_id
            WHERE b.fakulte_id = ?
            ORDER BY m.akademik_yil DESC
            """,
            (fakulte_id,),
        )
        years = [int(r[0]) for r in cur.fetchall()]
        if not years:
            return None, "Mufredat yili yok"

        for yil in years:
            cur.execute(
                """
                SELECT COUNT(DISTINCT m.bolum_id)
                FROM mufredat m
                JOIN bolum b ON b.bolum_id = m.bolum_id
                WHERE b.fakulte_id = ? AND m.akademik_yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
                """,
                (fakulte_id, yil, donem),
            )
            mevcut_bolum_adet = int(cur.fetchone()[0] or 0)
            cur.execute(
                """
                SELECT COUNT(DISTINCT m.bolum_id)
                FROM mufredat m
                JOIN bolum b ON b.bolum_id = m.bolum_id
                WHERE b.fakulte_id = ? AND m.akademik_yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
                """,
                (fakulte_id, yil + 1, donem),
            )
            sonraki_bolum_adet = int(cur.fetchone()[0] or 0)

            # Kaynak yil ile bir sonraki yilin kapsamını karsilastir.
            # Fakultedeki tum bolum sayisini zorlamak, legacy/eksik bolum verisinde
            # ayni yilin tekrar tekrar uretilmesine sebep olabiliyor.
            hedef_bolum_adet = mevcut_bolum_adet
            if mevcut_bolum_adet > 0 and sonraki_bolum_adet < hedef_bolum_adet:
                return yil, None

        return None, "Sonraki yil zaten mevcut"

    for fakulte_id, fakulte_adi in faculties:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        _normalize_mufredat_faculty_ids(cur)
        conn.commit()
        aday_yil, reason = _find_candidate_year(
            cur=cur,
            fakulte_id=fakulte_id,
            donem=donem,
        )
        conn.close()

        if aday_yil is None:
            summary["skipped"].append(
                {"fakulte_id": fakulte_id, "fakulte": fakulte_adi, "reason": reason}
            )
            continue

        result = generate_next_year_curricula(
            db_path=db_path,
            fakulte_id=fakulte_id,
            akademik_yil=aday_yil,
            donem=donem,
        )

        if result.get("ok"):
            summary["generated"].append(result)
        elif result.get("missing_criteria") or result.get("missing_curricula"):
            summary["skipped"].append(
                {
                    "fakulte_id": fakulte_id,
                    "fakulte": fakulte_adi,
                    "year": aday_yil,
                    "reason": result.get("error", "Kriterler hazir degil"),
                    "missing_criteria": result.get("missing_criteria", []) or [],
                    "missing_curricula": result.get("missing_curricula", []) or [],
                }
            )
        else:
            summary["ok"] = False
            summary["errors"].append(
                {
                    "fakulte_id": fakulte_id,
                    "fakulte": fakulte_adi,
                    "year": aday_yil,
                    "error": result.get("error", "Bilinmeyen hata"),
                }
            )
    return summary


def reset_future_curricula(db_path="data/adil_secmeli.db", base_year=2022):
    """
    Sadece base_year ve onceki yillari birakir.
    base_year sonrasi mufredat + havuz verilerini temizler.
    """
    result = {
        "ok": True,
        "base_year": int(base_year),
        "deleted_mufredat": 0,
        "deleted_mufredat_ders": 0,
        "deleted_havuz": 0,
        "normalized_curricula": 0,
    }

    if not os.path.exists(db_path):
        result["ok"] = False
        result["error"] = f"DB bulunamadi: {db_path}"
        return result

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        result["normalized_curricula"] = _normalize_mufredat_faculty_ids(cur)

        cur.execute(
            "SELECT mufredat_id FROM mufredat WHERE akademik_yil > ?",
            (int(base_year),),
        )
        mids = [int(r[0]) for r in cur.fetchall() if r and r[0] is not None]

        if mids:
            placeholders = ",".join("?" for _ in mids)
            cur.execute(
                f"DELETE FROM mufredat_ders WHERE mufredat_id IN ({placeholders})",
                tuple(mids),
            )
            result["deleted_mufredat_ders"] = int(cur.rowcount or 0)

        cur.execute("DELETE FROM mufredat WHERE akademik_yil > ?", (int(base_year),))
        result["deleted_mufredat"] = int(cur.rowcount or 0)

        cur.execute("DELETE FROM havuz WHERE yil > ?", (int(base_year),))
        result["deleted_havuz"] = int(cur.rowcount or 0)

        conn.commit()
        return result
    except Exception as exc:
        if conn:
            conn.rollback()
        result["ok"] = False
        result["error"] = str(exc)
        result["traceback"] = traceback.format_exc()
        return result
    finally:
        if conn:
            conn.close()


def _ensure_curriculum_log_table(cur):
    """Mufredat uretim log tablosu yoksa olusturur."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS curriculum_generation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            generated_count INTEGER NOT NULL DEFAULT 0,
            skipped_count INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            rounds INTEGER NOT NULL DEFAULT 0,
            summary_text TEXT
        )
    """)


def _write_curriculum_generation_log(db_path, overall):
    """
    Pipeline sonucu ozetini kalici log tablosuna yazar.
    overall: generate_curricula_until_stable donus degeri (generated, skipped, errors, rounds).
    """
    if not db_path or not os.path.exists(db_path):
        return
    conn = None
    try:
        from datetime import datetime
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        _ensure_curriculum_log_table(cur)
        generated = overall.get("generated", []) or []
        skipped = overall.get("skipped", []) or []
        errors = overall.get("errors", []) or []
        rounds = len(overall.get("rounds", []) or [])
        summary_parts = []
        for g in generated[:20]:
            summary_parts.append(
                f"{g.get('fakulte', '?')} {g.get('year_from')}->{g.get('year_to')}"
            )
        for s in skipped[:10]:
            summary_parts.append(f"[Atlanan] {s.get('fakulte', '?')} {s.get('reason', '')}")
        for e in errors[:10]:
            summary_parts.append(f"[Hata] {e.get('fakulte', '?')} {e.get('error', '')}")
        summary_text = "\n".join(summary_parts) if summary_parts else "Yeni uretim yok."
        created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            """
            INSERT INTO curriculum_generation_log
                (created_at, generated_count, skipped_count, error_count, rounds, summary_text)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (created_at, len(generated), len(skipped), len(errors), rounds, summary_text),
        )
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def generate_curricula_until_stable(db_path="data/adil_secmeli.db", donem="G", max_rounds=8):
    """
    Otomatik uretimi birden fazla tur calistirir.
    Ayni (fakulte, yil_from, yil_to) ciftleri tekrar etmeye basladiginda durur.
    """
    overall = {
        "ok": True,
        "rounds": [],
        "generated": [],
        "skipped": [],
        "errors": [],
    }
    seen_pairs = set()
    seen_skip_keys = set()
    seen_error_keys = set()

    for idx in range(int(max_rounds)):
        summary = auto_generate_next_year_curricula(db_path=db_path, donem=donem)
        overall["rounds"].append({"round": idx + 1, "summary": summary})

        gen_list = summary.get("generated", []) or []
        round_pairs = {
            (
                int(g.get("fakulte_id")),
                int(g.get("year_from")),
                int(g.get("year_to")),
            )
            for g in gen_list
            if g.get("fakulte_id") is not None and g.get("year_from") is not None and g.get("year_to") is not None
        }
        new_pairs = round_pairs - seen_pairs

        if not summary.get("ok"):
            overall["ok"] = False
        for err in (summary.get("errors", []) or []):
            key = (
                err.get("fakulte_id"),
                err.get("year"),
                err.get("error"),
            )
            if key not in seen_error_keys:
                seen_error_keys.add(key)
                overall["errors"].append(err)

        for sk in (summary.get("skipped", []) or []):
            key = (
                sk.get("fakulte_id"),
                sk.get("year"),
                sk.get("reason"),
            )
            if key not in seen_skip_keys:
                seen_skip_keys.add(key)
                overall["skipped"].append(sk)

        if gen_list:
            if new_pairs:
                for g in gen_list:
                    if g.get("fakulte_id") is None or g.get("year_from") is None or g.get("year_to") is None:
                        continue
                    pair = (
                        int(g.get("fakulte_id")),
                        int(g.get("year_from")),
                        int(g.get("year_to")),
                    )
                    if pair in new_pairs:
                        overall["generated"].append(g)
            else:
                # Ayni yil ciftleri tekrar olusuyorsa sonsuz donguyu engelle.
                break

        seen_pairs.update(round_pairs)

        # Yeni uretim yoksa dengeye ulasildi.
        if not gen_list:
            break

    _write_curriculum_generation_log(db_path, overall)
    return overall


def rebuild_school_curricula(db_path="data/adil_secmeli.db", base_year=2022, donem="G", max_rounds=8):
    """
    1) base_year sonrasi mufredatlari sifirlar
    2) kriterleri hazir olan yillari zincirleme otomatik yeniden uretir
    """
    reset = reset_future_curricula(db_path=db_path, base_year=base_year)
    if not reset.get("ok"):
        return {"ok": False, "reset": reset, "generation": None}

    generation = generate_curricula_until_stable(
        db_path=db_path,
        donem=donem,
        max_rounds=max_rounds,
    )
    return {
        "ok": bool(reset.get("ok")) and bool(generation.get("ok", True)),
        "reset": reset,
        "generation": generation,
    }


if __name__ == "__main__":
    run_automatic_scoring()
