# app/scripts/havuz_kumulatif_doldur.py
# Havuz tablosunu tüm yıllar için döngüsel/kümülatif doldurur.
# Bir önceki yılın statu, sayac, skor verisi bir sonraki yılın kaydını oluşturur.

import sqlite3
import os
import sys

# Proje kökünden import için (app/scripts -> proje kökü)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(os.path.dirname(_script_dir))
if _root not in sys.path:
    sys.path.insert(0, _root)
from app.services.havuz_karar import calculate_next_status


def get_db_path():
    base_dir = os.getcwd()
    for name in ("adil_secmeli.db", "adil_secimli.db"):
        for folder in ("data", ""):
            p = os.path.join(base_dir, folder, name)
            if os.path.exists(p):
                return p
    return os.path.join(base_dir, "data", "adil_secmeli.db")


def get_havuz_columns(cur):
    """Havuz tablosundaki kolonları döner."""
    cur.execute("PRAGMA table_info(havuz)")
    return [row[1] for row in cur.fetchall()]


def get_mufredat_ders_ids_for_year(cur, yil, fakulte_id=None):
    """Belirtilen yılda müfredatta olan ders_id listesini döner."""
    if fakulte_id is not None:
        cur.execute("""
            SELECT DISTINCT md.ders_id
            FROM mufredat m
            JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
            WHERE m.akademik_yil = ? AND m.fakulte_id = ?
        """, (yil, fakulte_id))
    else:
        cur.execute("""
            SELECT DISTINCT md.ders_id
            FROM mufredat m
            JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
            WHERE m.akademik_yil = ?
        """, (yil,))
    return {int(r[0]) for r in cur.fetchall()}


def get_mevcut_yillar(cur, fakulte_id=None):
    """Havuz veya müfredattan sistemdeki tüm yılları döner."""
    yillar = set()
    cur.execute("SELECT DISTINCT yil FROM havuz ORDER BY yil")
    for r in cur.fetchall():
        yillar.add(int(r[0]))
    cur.execute("SELECT DISTINCT akademik_yil FROM mufredat ORDER BY akademik_yil")
    for r in cur.fetchall():
        yillar.add(int(r[0]))
    if not yillar:
        yillar = {2020, 2021, 2022, 2023, 2024, 2025}
    return sorted(yillar)


def kumulatif_tum_yillar_doldur(
    db_path=None,
    fakulte_id=2,
    baslangic_yili=None,
    bitis_yili=None,
):
    """
    Havuz tablosunu tüm yıllar için döngüsel doldurur.
    - Bir önceki yılın statu, sayac, skor verisi alınır.
    - Bir sonraki yılın kaydı calculate_next_status ile oluşturulur.
    - Ders o yıl müfredatta yoksa yine havuzda kalır; statüsü kurallara göre güncellenir.
    """
    db_path = db_path or get_db_path()
    if not os.path.exists(db_path):
        print(f"❌ Veritabanı bulunamadı: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    yillar = get_mevcut_yillar(cur)
    if not yillar:
        print("❌ Havuz veya müfredatta yıl bulunamadı. Önce en az bir yıl verisi oluşturun.")
        conn.close()
        return

    baslangic_yili = baslangic_yili or min(yillar)
    bitis_yili = bitis_yili or max(yillar) + 1
    print(f"\n📅 Yıl aralığı: {baslangic_yili} .. {bitis_yili} (Fakülte ID: {fakulte_id})")

    # İlk yıl verisi yoksa, o yılı ders listesinden seed’le (statu=0, sayac=0, skor=0)
    cur.execute(
        "SELECT COUNT(*) FROM havuz WHERE yil = ? AND fakulte_id = ?",
        (baslangic_yili, fakulte_id),
    )
    if cur.fetchone()[0] == 0:
        print(f"🌱 {baslangic_yili} yılı havuzda yok; ders listesinden seed’leniyor...")
        try:
            cur.execute("""
                SELECT d.ders_id, d.ad FROM ders d
                WHERE d.fakulte_id = ? AND (d.DersTipi = 'Seçmeli' OR d.DersTipi = 'Secmeli' OR d.tip = 'Seçmeli')
            """, (fakulte_id,))
        except sqlite3.OperationalError:
            cur.execute("""
                SELECT ders_id, ad FROM ders WHERE fakulte_id = ?
            """, (fakulte_id,))
        dersler = cur.fetchall()
        for d in dersler:
            d_id = d[0]
            cur.execute(
                "INSERT INTO havuz (ders_id, fakulte_id, yil, statu, sayac, skor) VALUES (?, ?, ?, ?, ?, ?)",
                (d_id, fakulte_id, baslangic_yili, 0, 0, 0.0),
            )
        conn.commit()
        print(f"   {len(dersler)} ders eklendi.")

    # Yılları sırayla işle: onceki_yil verisi -> hedef_yil kaydı
    for hedef_yil in range(baslangic_yili + 1, bitis_yili + 1):
        onceki_yil = hedef_yil - 1
        print(f"\n🔄 {hedef_yil} yılı oluşturuluyor (önceki yıl: {onceki_yil})...")

        cur.execute("""
            SELECT ders_id, statu, sayac, skor
            FROM havuz
            WHERE yil = ? AND fakulte_id = ?
        """, (onceki_yil, fakulte_id))
        gecmis = cur.fetchall()

        if not gecmis:
            print(f"   ⚠️ {onceki_yil} verisi yok, atlanıyor.")
            continue

        # Bu yıl müfredatta olan dersler (komisyon kararı)
        mufredat_ids = get_mufredat_ders_ids_for_year(cur, hedef_yil, fakulte_id)

        # mufredat_ids INTEGER set; havuz.ders_id TEXT — int'e cast ederek karşılaştır
        eklenen = 0
        guncellenecekler = []
        eklenecekler = []

        for row in gecmis:
            raw_ders_id = row[0]
            try:
                ders_id_int = int(raw_ders_id)
            except (TypeError, ValueError):
                continue
            prev_statu = int(row[1]) if row[1] is not None else 0
            prev_sayac = int(row[2]) if row[2] is not None else 0
            prev_skor  = float(row[3]) if row[3] is not None else 0.0

            in_mufredat = ders_id_int in mufredat_ids
            yeni_statu, yeni_sayac = calculate_next_status(
                prev_statu, prev_sayac, in_mufredat
            )
            yeni_skor = prev_skor if yeni_statu != 1 else min(100, prev_skor + 1)

            cur.execute(
                "SELECT id FROM havuz WHERE CAST(ders_id AS INTEGER) = ? AND yil = ? AND fakulte_id = ?",
                (ders_id_int, hedef_yil, fakulte_id),
            )
            existing = cur.fetchone()
            if existing:
                guncellenecekler.append((yeni_statu, yeni_sayac, yeni_skor, existing[0]))
            else:
                eklenecekler.append(
                    (str(ders_id_int), fakulte_id, hedef_yil, yeni_statu, yeni_sayac, yeni_skor)
                )
                eklenen += 1

        if guncellenecekler:
            cur.executemany(
                "UPDATE havuz SET statu=?, sayac=?, skor=? WHERE id=?",
                guncellenecekler
            )
        if eklenecekler:
            cur.executemany(
                "INSERT INTO havuz (ders_id, fakulte_id, yil, statu, sayac, skor) VALUES (?,?,?,?,?,?)",
                eklenecekler
            )

        conn.commit()
        print(f"   ✅ {hedef_yil}: {len(gecmis)} kayıt işlendi ({eklenen} yeni eklendi).")

    conn.close()
    print("\n✅ Kümülatif havuz doldurma tamamlandı.")


def get_mufredat_listeleri():
    """Örnek müfredat kataloğu (isteğe bağlı kullanım)."""
    return {
        2023: [
            "Yenilenebilir Enerji Kaynakları", "Güç Elektroniği I", "Sayısal İşaret İşleme",
            "Mikroişlemciler", "Elektrik Enerjisi Dağıtımı", "Otomatik Kontrol Sistemleri II",
            "Gömülü Sistemler II", "Endüstriyel Otomasyon", "Haberleşme II", "Matlab ile Sayısal Analiz",
        ],
        2024: [
            "Elektrik Enerjisi Dağıtımı", "Güç Elektroniği II", "Sayısal İşaret İşleme",
            "Yüksek Gerilim Tekniği", "Nanoelektronik", "Gömülü Sistemler II", "Robotik",
            "Endüstriyel Otomasyon", "Bilgisayar Destekli Devre Analizi", "Antenler ve Propagasyon",
        ],
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Havuzu tüm yıllar için kümülatif doldurur.")
    p.add_argument("--db", default=None, help="Veritabanı yolu")
    p.add_argument("--fakulte", type=int, default=2, help="Fakülte ID")
    p.add_argument("--baslangic", type=int, default=None, help="Başlangıç yılı")
    p.add_argument("--bitis", type=int, default=None, help="Bitiş yılı")
    args = p.parse_args()
    kumulatif_tum_yillar_doldur(
        db_path=args.db,
        fakulte_id=args.fakulte,
        baslangic_yili=args.baslangic,
        bitis_yili=args.bitis,
    )
