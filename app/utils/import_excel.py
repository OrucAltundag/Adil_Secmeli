"""
Excel'den veri aktarım modülü.
- Data Cleaning: NaN/Null toleranslı
- Upsert: Mükerrer kayıt kontrolü
- Fakülte/Bölüm standart eşleştirme
- Hata loglama
"""
import logging
import os
import sys
import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)

from app.db.database import SessionLocal, get_session, dispose_session
from app.db.models import Fakulte, Bolum, Ders, Performans, Populerlik

LOG_DIR = os.path.join(parent_dir, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "import_excel.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("import_excel")


# --- Fakülte/Bölüm standart eşleştirme ---
FAKULTE_ALIAS = {
    "müh. fak.": "Mühendislik Fakültesi",
    "mühendislik fak.": "Mühendislik Fakültesi",
    "mühendislik ve doğa bilimleri": "Mühendislik ve Doğa Bilimleri Fakültesi",
    "muhendislik": "Mühendislik Fakültesi",
    "fen edebiyat": "Fen Edebiyat Fakültesi",
    "iibf": "İktisadi ve İdari Bilimler Fakültesi",
    "iibf fak.": "İktisadi ve İdari Bilimler Fakültesi",
}

BOLUM_ALIAS = {
    "bil. müh.": "Bilgisayar Mühendisliği",
    "bilgisayar müh.": "Bilgisayar Mühendisliği",
    "elk. müh.": "Elektrik-Elektronik Mühendisliği",
    "elektrik-elektronik": "Elektrik-Elektronik Mühendisliği",
}


def _normalize_text(s: str) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    return str(s).strip().lower()


def _resolve_fakulte(raw: str) -> str:
    n = _normalize_text(raw)
    for alias, canonical in FAKULTE_ALIAS.items():
        if alias in n or n in alias:
            return canonical
    return str(raw).strip() if raw else "Bilinmeyen Fakülte"


def _resolve_bolum(raw: str) -> str:
    n = _normalize_text(raw)
    for alias, canonical in BOLUM_ALIAS.items():
        if alias in n or n in alias:
            return canonical
    return str(raw).strip() if raw else "Genel Bölüm"


def safe_int(value, default=0):
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return default
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_float(value, default=0.0):
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_str(value, default=""):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    s = str(value).strip()
    return s if s else default


def clean_dataframe(df: pd.DataFrame, required_cols=None):
    """
    NaN/Null temizliği, boş satırları at.
    """
    required_cols = required_cols or ["FakülteAdı", "BölümAdı", "DersAdı"]
    for col in required_cols:
        if col not in df.columns:
            logger.warning(f"Eksik kolon: {col}")
            return pd.DataFrame()

    baslangic = len(df)
    df = df.dropna(subset=required_cols, how="all")
    df = df.fillna({"FakülteAdı": "", "BölümAdı": "", "DersAdı": ""})
    df = df[df["FakülteAdı"].astype(str).str.strip() != ""]
    df = df[df["DersAdı"].astype(str).str.strip() != ""]
    bitis = len(df)
    if baslangic != bitis:
        logger.info(f"Temizlik: {baslangic - bitis} satır atıldı")
    return df


def import_data(file_path, clear_existing=False):
    logger.info(f"Dosya okunuyor: {file_path}")

    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        logger.exception(f"Dosya okunamadı: {e}")
        return

    df.columns = [str(c).strip() for c in df.columns]
    df = clean_dataframe(df)
    if df.empty:
        logger.warning("Temizleme sonrası veri kalmadı.")
        return

    db = get_session()
    counters = {"fakulte": 0, "bolum": 0, "ders_eklenen": 0, "ders_guncellenen": 0, "hata": 0}
    fakulte_map = {}
    bolum_map = {}

    try:
        for f in db.query(Fakulte).all():
            fakulte_map[_normalize_text(f.ad)] = (f.fakulte_id, f.ad)
        for b in db.query(Bolum).all():
            bolum_map[_normalize_text(b.ad)] = (b.bolum_id, b.ad)
    except Exception as e:
        logger.exception(f"Cache yükleme hatası: {e}")
        dispose_session()
        return

    if clear_existing:
        try:
            db.query(Performans).delete()
            db.query(Populerlik).delete()
            db.query(Ders).delete()
            db.commit()
            logger.info("Mevcut Ders/Performans/Populerlik temizlendi.")
        except Exception as e:
            db.rollback()
            logger.warning(f"Temizleme uyarısı: {e}")

    for index, row in df.iterrows():
        try:
            fak_ad_raw = safe_str(row.get("FakülteAdı", ""), "Bilinmeyen")
            bol_ad_raw = safe_str(row.get("BölümAdı", ""), "Genel")
            fak_ad = _resolve_fakulte(fak_ad_raw)
            bol_ad = _resolve_bolum(bol_ad_raw)
            ders_ad = safe_str(row.get("DersAdı", ""), "İsimsiz Ders")
            ders_kod = safe_str(row.get("DersID", ""), f"KOD-{index}")

            if not ders_ad:
                continue

            # Fakülte upsert
            fak_key = _normalize_text(fak_ad)
            if fak_key not in fakulte_map:
                yeni = Fakulte(ad=fak_ad, okul_id=1, tip="Lisans", kampus="Merkez")
                db.add(yeni)
                db.flush()
                fakulte_map[fak_key] = (yeni.fakulte_id, fak_ad)
                counters["fakulte"] += 1
            f_id = fakulte_map[fak_key][0]

            # Bölüm upsert
            bol_key = _normalize_text(bol_ad)
            if bol_key not in bolum_map:
                yeni = Bolum(ad=bol_ad, fakulte_id=f_id)
                db.add(yeni)
                db.flush()
                bolum_map[bol_key] = (yeni.bolum_id, bol_ad)
                counters["bolum"] += 1
            b_id = bolum_map[bol_key][0]

            # Ders upsert (kod ile kontrol)
            mevcut = db.query(Ders).filter(Ders.kod == ders_kod).first()
            kredi_val = safe_int(row.get("Teorik", 0)) + safe_int(row.get("Uygulama", 0))
            akts_val = safe_int(row.get("AKTS", 3))
            tip_val = safe_str(row.get("DersTipi", ""), "Seçmeli")
            bilgi_val = safe_str(row.get("Dersİçeriği", ""), "İçerik girilmedi.")

            if mevcut:
                mevcut.ad = ders_ad
                mevcut.fakulte_id = f_id
                mevcut.kredi = kredi_val
                mevcut.akts = akts_val
                mevcut.tip = tip_val
                mevcut.bilgi = bilgi_val
                ders_id = mevcut.ders_id
                counters["ders_guncellenen"] += 1
            else:
                ders = Ders(
                    kod=ders_kod,
                    ad=ders_ad,
                    fakulte_id=f_id,
                    kredi=kredi_val,
                    akts=akts_val,
                    tip=tip_val,
                    bilgi=bilgi_val,
                    onkosul=None,
                )
                db.add(ders)
                db.flush()
                ders_id = ders.ders_id
                counters["ders_eklenen"] += 1

            # Performans (sadece yeni dersler için veya upsert)
            donem = safe_str(row.get("Yarıyıl", ""), "Güz")
            ort_basari = safe_float(row.get("OrtalamaBaşarı"), 50.0)
            katilimci = safe_int(row.get("PopülariteSayı"), 0)

            perf = db.query(Performans).filter(
                Performans.ders_id == ders_id,
                Performans.akademik_yil == 2024,
                Performans.donem == donem,
            ).first()
            if perf:
                perf.ortalama_not = ort_basari
                perf.basari_orani = max(0.0, min(1.0, ort_basari / 100.0))
            else:
                perf = Performans(
                    ders_id=ders_id,
                    akademik_yil=2024,
                    donem=donem,
                    ortalama_not=ort_basari,
                    basari_orani=max(0.0, min(1.0, ort_basari / 100.0)),
                )
                db.add(perf)

            # Popülerlik
            pop_puan = safe_float(row.get("PopülerlikPuanı"), 0.0)
            doluluk = min(1.0, katilimci / 50.0) if katilimci else 0.0
            pop = db.query(Populerlik).filter(
                Populerlik.ders_id == ders_id,
                Populerlik.akademik_yil == 2024,
                Populerlik.donem == donem,
            ).first()
            if pop:
                pop.talep_sayisi = katilimci
                pop.kontenjan = 50
                pop.doluluk_orani = doluluk
            else:
                pop = Populerlik(
                    ders_id=ders_id,
                    akademik_yil=2024,
                    donem=donem,
                    talep_sayisi=katilimci,
                    kontenjan=50,
                    doluluk_orani=doluluk,
                )
                db.add(pop)

            db.commit()

        except Exception as e:
            counters["hata"] += 1
            logger.exception(f"Satır {index + 2} hatası: {e}")
            db.rollback()

    dispose_session()
    logger.info(
        f"Tamamlandı: +{counters['fakulte']} Fakülte, +{counters['bolum']} Bölüm, "
        f"+{counters['ders_eklenen']} Ders, ~{counters['ders_guncellenen']} güncelleme, {counters['hata']} hata"
    )


if __name__ == "__main__":
    excel_path = os.path.join(parent_dir, "data", "dersler_master.xlsx")
    if os.path.exists(excel_path):
        import_data(excel_path, clear_existing=False)
    else:
        logger.error(f"Dosya bulunamadı: {excel_path}")
