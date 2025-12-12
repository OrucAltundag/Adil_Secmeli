import pandas as pd
import os
import sys
import math

# Proje dizinini yola ekle
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_dir)

from app.db.database import SessionLocal, engine, Base
from app.db.models import Fakulte, Bolum, Ders, Performans, Populerlik

def safe_int(value, default=0):
    """Güvenli tamsayı dönüşümü (Boş veya hatalıysa default döner)"""
    try:
        if pd.isna(value): return default
        return int(float(value))
    except:
        return default

def safe_float(value, default=0.0):
    """Güvenli ondalık sayı dönüşümü"""
    try:
        if pd.isna(value): return default
        return float(value)
    except:
        return default

def safe_str(value, default=""):
    """Güvenli metin dönüşümü"""
    if pd.isna(value): return default
    return str(value).strip()

def import_data(file_path):
    print(f"📂 '{file_path}' dosyası okunuyor...")
    
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"❌ Hata: Dosya okunamadı. {e}")
        return

    # --- 1. TEMİZLİK AŞAMASI ---
    # Fakülte, Bölüm veya Ders adı boş olan satırları atıyoruz (Bunlar olmazsa kayıt yapılamaz)
    baslangic_sayisi = len(df)
    df = df.dropna(subset=['FakülteAdı', 'BölümAdı', 'DersAdı'])
    bitis_sayisi = len(df)
    
    if baslangic_sayisi != bitis_sayisi:
        print(f"⚠️ Uyarı: {baslangic_sayisi - bitis_sayisi} adet boş/hatalı satır temizlendi.")

    db = SessionLocal()
    
    # Verileri temizle (Temiz kurulum için)
    print("🧹 Eski veriler (Ders, Performans, Populerlik) temizleniyor...")
    try:
        db.query(Performans).delete()
        db.query(Populerlik).delete()
        db.query(Ders).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Temizleme uyarısı: {e}")

    print("🚀 Veri aktarımı başladı...")
    
    counters = {"fakulte": 0, "bolum": 0, "ders": 0}
    
    # Cache (Performans için mevcut verileri hafızaya al)
    fakulte_map = {f.ad: f.fakulte_id for f in db.query(Fakulte).all()}
    bolum_map = {b.ad: b.bolum_id for b in db.query(Bolum).all()}

    for index, row in df.iterrows():
        try:
            # Veri Güvenliği: Boşlukları temizle ve string olduğundan emin ol
            fak_ad = safe_str(row['FakülteAdı'], "Bilinmeyen Fakülte")
            bol_ad = safe_str(row['BölümAdı'], "Genel Bölüm")
            ders_ad = safe_str(row['DersAdı'], "İsimsiz Ders")
            ders_kod = safe_str(row['DersID'], f"KOD-{index}") # Kod yoksa geçici kod ver

            # 1. Fakülte Kontrolü / Ekleme
            if fak_ad not in fakulte_map:
                yeni_fak = Fakulte(ad=fak_ad, okul_id=1, tip="Lisans", kampus="Merkez") 
                db.add(yeni_fak)
                db.commit()
                db.refresh(yeni_fak)
                fakulte_map[fak_ad] = yeni_fak.fakulte_id
                counters["fakulte"] += 1
            
            f_id = fakulte_map[fak_ad]

            # 2. Bölüm Kontrolü / Ekleme
            if bol_ad not in bolum_map:
                yeni_bol = Bolum(ad=bol_ad, fakulte_id=f_id)
                db.add(yeni_bol)
                db.commit()
                db.refresh(yeni_bol)
                bolum_map[bol_ad] = yeni_bol.bolum_id
                counters["bolum"] += 1
                
            b_id = bolum_map[bol_ad]

            # 3. Ders Ekleme
            # Kredi ve AKTS hesaplama (Hata varsa 0 kabul et)
            kredi_val = safe_int(row.get('Teorik', 0)) + safe_int(row.get('Uygulama', 0))
            akts_val = safe_int(row.get('AKTS', 3)) # Varsayılan 3 AKTS

            ders = Ders(
                kod=ders_kod,
                ad=ders_ad,
                fakulte_id=f_id,
                # bolum_id modelinizde varsa burayı açın: bolum_id=b_id,
                kredi=kredi_val,
                akts=akts_val,
                tip=safe_str(row.get('DersTipi'), 'Seçmeli'),
                bilgi=safe_str(row.get('Dersİçeriği'), 'İçerik bilgisi girilmemiş.'),
                onkosul=None
            )
            db.add(ders)
            db.commit()
            db.refresh(ders)
            counters["ders"] += 1

            # 4. Performans ve Popülerlik Verisini Ekleme (Varsayılan Değerlerle)
            # Excel'de boşsa: Başarı=50, Katılımcı=0 varsayılır.
            ort_basari = safe_float(row.get('OrtalamaBaşarı'), 50.0)
            katilimci = safe_int(row.get('PopülariteSayı'), 0)
            pop_puan = safe_float(row.get('PopülerlikPuanı'), 0.0)
            
            # Yarıyıl bilgisini güvenli al
            donem_bilgisi = safe_str(row.get('Yarıyıl'), 'Güz')

            perf = Performans(
                ders_id=ders.ders_id,
                akademik_yil=2024,
                donem=donem_bilgisi,
                ortalama_not=ort_basari,
                basari_orani=ort_basari / 100.0,
                katilimci_sayisi=katilimci
            )
            db.add(perf)

            pop = Populerlik(
                ders_id=ders.ders_id,
                akademik_yil=2024,
                donem=donem_bilgisi,
                tercih_sayisi=katilimci,
                tercih_orani=pop_puan
            )
            db.add(pop)
            db.commit()
            
        except Exception as inner_e:
            print(f"⚠️ Satır {index+2} hatası (atlandı): {inner_e}")
            db.rollback()
            continue

    print(f"✅ İŞLEM TAMAMLANDI!")
    print(f"📊 Eklenenler: {counters['fakulte']} Fakülte, {counters['bolum']} Bölüm, {counters['ders']} Ders.")

if __name__ == "__main__":
    excel_dosyasi = os.path.join(parent_dir, "data", "dersler_master.xlsx")
    
    if os.path.exists(excel_dosyasi):
        import_data(excel_dosyasi)
    else:
        print(f"❌ Dosya bulunamadı: {excel_dosyasi}")