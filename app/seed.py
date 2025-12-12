# seed.py,  models.py şemanla birebir çalışır: 
#küçük bir demo verisi basar, Anket puanlarını toplar (A_norm), Performans/Popülerlik’i normalize eder (B_norm/P_norm), sonra Skor tablosuna skor_top yazar.
#
#Çalıştırmak için: python -m app.seed


# app/seed.py
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import engine, SessionLocal, Base
from app.db import models as M


# -----------------------------
# Yardımcılar
# -----------------------------
def reset_db():
    """Tabloları oluştur (drop yapmadan). İlk kez koşuyorsan yeni kurar, tekrar koşuyorsan eksikleri tamamlar."""
    Base.metadata.create_all(bind=engine)


def clear_demo(session: Session):
    """Demo verilerini temizlemek istersen çağır (tamamen opsiyonel)."""
    # Dikkat: FK sırasına göre sil
    for tbl in [
        M.Skor, M.AnketSonuclari, M.AnketCevap, M.AnketForm,
        M.Populerlik, M.Performans, M.Kayit,
        M.MufredatDers, M.Mufredat, M.DersOgretim,
        M.OgrenciEngel, M.Havuz,
        M.OgretimGorevlisi, M.Ogrenci, M.Ders, M.Bolum, M.Fakulte, M.Okul
    ]:
        session.query(tbl).delete()
    session.commit()


def minmax(values):
    """None'ları sıfır say, min-max norm 0..1 döndür."""
    vs = [v if v is not None else 0.0 for v in values]
    if not vs:
        return []
    vmin, vmax = min(vs), max(vs)
    if vmax == vmin:
        return [0.0 for _ in vs]
    return [(v - vmin) / (vmax - vmin) for v in vs]


# -----------------------------
# Demo veri bas
# -----------------------------
def seed_base(session: Session):
    # 1) Okul
    okul = M.Okul(school_id=1, ad="GİBTÜ", kampus="Merkez")
    session.merge(okul)

    # 2) Fakülteler
    f_muh = M.Fakulte(fakulte_id=1, ad="Mühendislik Fakültesi", okul_id=1, tip="Lisans", kampus="A Blok")
    f_iibf = M.Fakulte(fakulte_id=2, ad="İİBF", okul_id=1, tip="Lisans", kampus="B Blok")
    session.merge(f_muh)
    session.merge(f_iibf)

    # 3) Bölümler
    b_bil = M.Bolum(bolum_id=1, ad="Bilgisayar Mühendisliği", fakulte_id=1)
    b_end = M.Bolum(bolum_id=2, ad="Endüstri Mühendisliği", fakulte_id=1)
    session.merge(b_bil)
    session.merge(b_end)

    # 4) Dersler (fakülte 1 için birkaç ders)
    d_alg = M.Ders(ders_id=101, kod="BIL101", ad="Algoritmalar", kredi=4, akts=6, bilgi="Temel algoritmalar", tip="Zorunlu", fakulte_id=1)
    d_veri = M.Ders(ders_id=102, kod="BIL302", ad="Veritabanı Sistemleri", kredi=4, akts=6, bilgi="SQL/NoSQL", tip="Seçmeli", fakulte_id=1)
    d_ml = M.Ders(ders_id=103, kod="BIL401", ad="Makine Öğrenmesi", kredi=4, akts=6, bilgi="Denetimli/Denetimsiz", tip="Seçmeli", fakulte_id=1, onkosul=101)
    d_py = M.Ders(ders_id=104, kod="BIL202", ad="Python ile Uygulama", kredi=3, akts=5, bilgi="Pratik Python", tip="Seçmeli", fakulte_id=1)
    d_ui = M.Ders(ders_id=105, kod="BIL351", ad="Arayüz Tasarımı", kredi=3, akts=5, bilgi="UI/UX", tip="Seçmeli", fakulte_id=1)
    session.merge(d_alg); session.merge(d_veri); session.merge(d_ml); session.merge(d_py); session.merge(d_ui)

    # 5) Öğrenciler
    s1 = M.Ogrenci(ogr_id=1001, ad="Ayşe", soyad="Demir", email="ayse@gibtu.edu", ogrenci_no="2025001", fakulte_id=1)
    s2 = M.Ogrenci(ogr_id=1002, ad="Mehmet", soyad="Kaya", email="mehmet@gibtu.edu", ogrenci_no="2025002", fakulte_id=1)
    s3 = M.Ogrenci(ogr_id=1003, ad="Elif", soyad="Yıldız", email="elif@gibtu.edu", ogrenci_no="2025003", fakulte_id=1)
    s4 = M.Ogrenci(ogr_id=1004, ad="Burak", soyad="Aslan", email="burak@gibtu.edu", ogrenci_no="2025004", fakulte_id=1)
    s5 = M.Ogrenci(ogr_id=1005, ad="Zeynep", soyad="Koç", email="zeynep@gibtu.edu", ogrenci_no="2025005", fakulte_id=1)
    for s in (s1, s2, s3, s4, s5): session.merge(s)

    # 6) Öğretim Görevlileri
    o1 = M.OgretimGorevlisi(ogrt_id=201, ad="Selim", soyad="Öztürk", unvan="Dr. Öğr. Üyesi", email="selim@gibtu.edu",
                            tel="5550001", durum="Aktif", memnuniyet_puani=4.2, kidem_yil=6, atanma_tarihi=date(2020,9,1),
                            school_id=1, fakulte_id=1, basarim_ort=3.1)
    o2 = M.OgretimGorevlisi(ogrt_id=202, ad="Hande", soyad="Arslan", unvan="Doç. Dr.", email="hande@gibtu.edu",
                            tel="5550002", durum="Aktif", memnuniyet_puani=4.6, kidem_yil=9, atanma_tarihi=date(2017,9,1),
                            school_id=1, fakulte_id=1, basarim_ort=3.3)
    o3 = M.OgretimGorevlisi(ogrt_id=203, ad="Kemal", soyad="Şen", unvan="Öğr. Gör.", email="kemal@gibtu.edu",
                            tel="5550003", durum="Aktif", memnuniyet_puani=4.0, kidem_yil=3, atanma_tarihi=date(2022,9,1),
                            school_id=1, fakulte_id=1, basarim_ort=3.0)
    for o in (o1, o2, o3): session.merge(o)

    # 7) Ders_Öğretim (2025-2026 Güz)
    do1 = M.DersOgretim(ders_ogrt_id=1, ders_id=101, ogrt_id=201, rol="Ana Eğitmen", donem="Güz", akademik_yil=2025, ders_saati=4, katki_oran=1.0, not_ortalaması=3.0, kontenjan=80)
    do2 = M.DersOgretim(ders_ogrt_id=2, ders_id=102, ogrt_id=202, rol="Ana Eğitmen", donem="Güz", akademik_yil=2025, ders_saati=3, katki_oran=1.0, not_ortalaması=3.2, kontenjan=60)
    do3 = M.DersOgretim(ders_ogrt_id=3, ders_id=103, ogrt_id=202, rol="Ana Eğitmen", donem="Güz", akademik_yil=2025, ders_saati=3, katki_oran=1.0, not_ortalaması=3.1, kontenjan=50)
    do4 = M.DersOgretim(ders_ogrt_id=4, ders_id=104, ogrt_id=203, rol="Ana Eğitmen", donem="Güz", akademik_yil=2025, ders_saati=3, katki_oran=1.0, not_ortalaması=3.3, kontenjan=70)
    do5 = M.DersOgretim(ders_ogrt_id=5, ders_id=105, ogrt_id=201, rol="Ana Eğitmen", donem="Güz", akademik_yil=2025, ders_saati=2, katki_oran=1.0, not_ortalaması=3.4, kontenjan=40)
    for x in (do1, do2, do3, do4, do5): session.merge(x)

    # 8) Müfredat (2025 Güz, Bilgisayar)
    muf = M.Mufredat(mufredat_id=1, fakulte_id=1, akademik_yil=2025, bolum_id=1, donem="Güz", durum="Onaylı", versiyon=1)
    session.merge(muf)
    for (md_id, ders_id) in [(1,101),(2,102),(3,103)]:
        session.merge(M.MufredatDers(mders_id=md_id, mufredat_id=1, ders_id=ders_id))

    # 9) Havuz (gelecek dönem açılabilecek seçmeliler)
    hv1 = M.Havuz(havuz_id=1, ders_id=102, fakulte_id=1, secilebilirlik_durumu=True, kontenjan_durumu="Açık",
                  on_kosul_durumu="Yok", ogrenci_dinlendirme_durumu="Yok",
                  acilis_tarihi=date(2025,12,1), kapanis_tarihi=date(2026,1,15), durum_degeri=0.5)
    hv2 = M.Havuz(havuz_id=2, ders_id=103, fakulte_id=1, secilebilirlik_durumu=True, kontenjan_durumu="Açık",
                  on_kosul_durumu="Algoritmalar", ogrenci_dinlendirme_durumu="Yok",
                  acilis_tarihi=date(2025,12,1), kapanis_tarihi=date(2026,1,15), durum_degeri=0.6)
    hv3 = M.Havuz(havuz_id=3, ders_id=104, fakulte_id=1, secilebilirlik_durumu=True, kontenjan_durumu="Açık",
                  on_kosul_durumu="Yok", ogrenci_dinlendirme_durumu="Yok",
                  acilis_tarihi=date(2025,12,1), kapanis_tarihi=date(2026,1,15), durum_degeri=0.4)
    hv4 = M.Havuz(havuz_id=4, ders_id=105, fakulte_id=1, secilebilirlik_durumu=True, kontenjan_durumu="Açık",
                  on_kosul_durumu="Yok", ogrenci_dinlendirme_durumu="Yok",
                  acilis_tarihi=date(2025,12,1), kapanis_tarihi=date(2026,1,15), durum_degeri=0.4)
    for hv in (hv1, hv2, hv3, hv4): session.merge(hv)

    # 10) Kayıt (geçmiş dönem)
    k1 = M.Kayit(kayit_id=1, ogr_id=1001, ders_id=101, akademik_yil=2025, donem="Güz", kayit_turu="ogrenci", kayit_tarih=datetime(2025,9,5), durum="basarili", ogrt_id=201)
    k2 = M.Kayit(kayit_id=2, ogr_id=1002, ders_id=101, akademik_yil=2025, donem="Güz", kayit_turu="ogrenci", kayit_tarih=datetime(2025,9,6), durum="basarili", ogrt_id=201)
    k3 = M.Kayit(kayit_id=3, ogr_id=1003, ders_id=102, akademik_yil=2025, donem="Güz", kayit_turu="ogrenci", kayit_tarih=datetime(2025,9,6), durum="basarili", ogrt_id=202)
    for k in (k1, k2, k3): session.merge(k)

    # 11) Performans (geçmiş)
    p1 = M.Performans(pfrs_id=1, ders_id=101, akademik_yil=2025, donem="Güz", ogrt_id=201, ortalama_not=3.0, basari_orani=0.85, katilimci_sayisi=75)
    p2 = M.Performans(pfrs_id=2, ders_id=102, akademik_yil=2025, donem="Güz", ogrt_id=202, ortalama_not=3.2, basari_orani=0.80, katilimci_sayisi=60)
    p3 = M.Performans(pfrs_id=3, ders_id=103, akademik_yil=2025, donem="Güz", ogrt_id=202, ortalama_not=3.1, basari_orani=0.78, katilimci_sayisi=50)
    for p in (p1, p2, p3): session.merge(p)

    # 12) Popülerlik (geçmiş seçim sinyali)
    pop1 = M.Populerlik(pop_id=1, ders_id=102, akademik_yil=2025, donem="Güz", tercih_sayisi=60, tercih_orani=0.30)
    pop2 = M.Populerlik(pop_id=2, ders_id=103, akademik_yil=2025, donem="Güz", tercih_sayisi=50, tercih_orani=0.25)
    pop3 = M.Populerlik(pop_id=3, ders_id=104, akademik_yil=2025, donem="Güz", tercih_sayisi=40, tercih_orani=0.20)
    pop4 = M.Populerlik(pop_id=4, ders_id=105, akademik_yil=2025, donem="Güz", tercih_sayisi=30, tercih_orani=0.15)
    for pop in (pop1, pop2, pop3, pop4): session.merge(pop)

    session.commit()


def seed_survey_and_scores(session: Session):
    # 13) Anket Formu (2026 Bahar – Fakülte 1)
    form = M.AnketForm(form_id=1, ad="Bahar 2026 Seçmeli Ders Anketi",
                       akademik_yil=2026, donem="Bahar", fakulte_id=1,
                       baslangic_tarih=date(2025,12,1), bitis_tarih=date(2026,1,15),
                       aktif_mi=True, aciklama="Top-3 sıralı tercih (Borda)")
    session.merge(form)
    session.commit()

    # 13) Anket Cevapları (Top-3; 5 öğrenciden örnek)
    # Borda puanı: rank=1 -> 3, 2 -> 2, 3 -> 1; siddet (1..5) ağırlığı uygulanacak
    cevaplar = [
        # ogr_id, ders_id, rank, siddet
        (1001, 103, 1, 5), (1001, 102, 2, 5), (1001, 104, 3, 4),
        (1002, 102, 1, 5), (1002, 103, 2, 4), (1002, 105, 3, 3),
        (1003, 104, 1, 4), (1003, 102, 2, 5), (1003, 105, 3, 3),
        (1004, 103, 1, 5), (1004, 104, 2, 4), (1004, 102, 3, 5),
        (1005, 104, 1, 5), (1005, 103, 2, 4), (1005, 102, 3, 5),
    ]
    # yaz ve puan hesapla
    session.query(M.AnketCevap).delete()  # demo temiz
    cid = 1
    for (ogr, ders, r, s) in cevaplar:
        borda = 3 if r == 1 else (2 if r == 2 else 1)
        puan = float(borda) * (float(s) / 5.0)
        ac = M.AnketCevap(cevap_id=cid, form_id=1, ogr_id=ogr, ders_id=ders,
                          rank=r, siddet=s, puan=puan,
                          cevap_tarihi=datetime.now(), ip_hash=None)
        session.add(ac)
        cid += 1
    session.commit()

    # 14) Anket Sonuçları (toplama + A_norm 0..100)
    session.query(M.AnketSonuclari).delete()
    rows = (
        session.query(
            M.AnketCevap.form_id,
            M.AnketCevap.ders_id,
            func.sum(M.AnketCevap.puan).label("toplam_puan"),
            func.count(M.AnketCevap.cevap_id).label("oy_sayisi"),
            func.avg(M.AnketCevap.siddet).label("ortalama_siddet"),
        )
        .filter(M.AnketCevap.form_id == 1)
        .group_by(M.AnketCevap.form_id, M.AnketCevap.ders_id)
        .all()
    )
    # min-max normalize
    toplams = [r.toplam_puan for r in rows]
    norm = minmax(toplams)
    for (r, a_norm) in zip(rows, norm):
        session.add(M.AnketSonuclari(
            anketsonuc_id=None,
            ders_id=r.ders_id, form_id=r.form_id,
            toplam_puan=float(r.toplam_puan),
            oy_sayisi=int(r.oy_sayisi),
            ortalama_siddet=float(r.ortalama_siddet if r.ortalama_siddet else 0),
            a_norm=round(a_norm * 100.0, 2),  # 0..100
            hesaplanma_tarihi=datetime.now()
        ))
    session.commit()

    # 15) Skor (B_norm / P_norm / A_norm -> skor_top)
    # B_norm: Performans (geçmiş 2025 Güz)
    perf = session.query(M.Performans).filter(M.Performans.akademik_yil==2025, M.Performans.donem=="Güz").all()
    perf_map = {}
    for p in perf:
        # basit bir başarı ölçütü: basari_orani (0..1) * ortalama_not (0..4 varsay)
        perf_map.setdefault(p.ders_id, 0.0)
        perf_map[p.ders_id] = max(perf_map[p.ders_id], (p.basari_orani or 0) * (p.ortalama_not or 0))

    # P_norm: Popülerlik (geçmiş 2025 Güz) -> tercih_sayisi
    pops = session.query(M.Populerlik).filter(M.Populerlik.akademik_yil==2025, M.Populerlik.donem=="Güz").all()
    pop_map = {p.ders_id: (p.tercih_sayisi or 0) for p in pops}

    # A_norm: AnketSonuclari (2026 Bahar form_id=1)
    anket_son = session.query(M.AnketSonuclari).filter(M.AnketSonuclari.form_id==1).all()
    a_map = {a.ders_id: (a.a_norm or 0.0) for a in anket_son}

    ders_ids = sorted(set(list(perf_map.keys()) + list(pop_map.keys()) + list(a_map.keys())))
    # normalize B ve P
    b_vals = [perf_map.get(d, 0.0) for d in ders_ids]
    p_vals = [pop_map.get(d, 0.0) for d in ders_ids]
    b_norm = minmax(b_vals)  # 0..1
    p_norm = minmax(p_vals)  # 0..1

    # A zaten 0..100; 0..1'e çekelim skor için
    a_vals = [a_map.get(d, 0.0)/100.0 for d in ders_ids]

    # ağırlıklar
    wB, wP, wA = 0.5, 0.3, 0.2
    session.query(M.Skor).delete()
    for i, d in enumerate(ders_ids):
        score = wB*b_norm[i] + wP*p_norm[i] + wA*a_vals[i]
        session.add(M.Skor(
            skor_id=None,
            ders_id=d,
            akademik_yil=2026,
            donem="Bahar",
            b_norm=round(b_norm[i]*100, 2),   # rapor kolaylığı için %
            p_norm=round(p_norm[i]*100, 2),
            a_norm=round(a_vals[i]*100, 2),
            g_norm=None,
            skor_top=round(score*100, 2),
            hesap_tarih=datetime.now()
        ))
    session.commit()


def main():
    reset_db()
    session = SessionLocal()
    try:
        # clear_demo(session)  # İstersen ilk satırda aç, demo verilerini sıfırlar
        seed_base(session)
        seed_survey_and_scores(session)
        print("Seed tamam ✅ — demo verileri, A/B/P normalizasyonları ve skorlar yazıldı.")
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
