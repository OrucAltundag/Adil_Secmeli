# -*- coding: utf-8 -*-
"""
havuz tablosunu 2022 için sıfırdan, deterministik kur.

Kural (kullanıcı): İlgili fakültedeki BÜTÜN seçmeli dersler havuza çekilir;
müfredatta olan o dönem için statu=1, olmayan statu=0. Sadece 2022 kalır.
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).parent.parent / "data" / "adil_secmeli.db"
YIL = 2022


def main():
    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()

    print("1) Tum havuz kayitlari siliniyor (2022-2030 bozuk veri)...")
    cur.execute("SELECT COUNT(*) FROM havuz")
    print(f"   Silinen: {cur.fetchone()[0]} satir")
    cur.execute("DELETE FROM havuz")
    conn.commit()

    # 2022 mufredatı olan fakülteler
    cur.execute(
        "SELECT DISTINCT fakulte_id FROM mufredat WHERE akademik_yil = ?",
        (YIL,),
    )
    fakulteler = [int(r[0]) for r in cur.fetchall()]
    print(f"2) 2022 mufredati olan fakulteler: {fakulteler}")

    # ders_id -> mufredat donem (2022). Bu ders müfredatta hangi dönemde?
    cur.execute(
        """
        SELECT md.ders_id, m.donem
        FROM mufredat m
        JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
        WHERE m.akademik_yil = ?
        """,
        (YIL,),
    )
    ders_donem = {int(r[0]): str(r[1]) for r in cur.fetchall()}
    print(f"   Mufredattaki ders sayisi: {len(ders_donem)}")

    toplam = 0
    for fak in fakulteler:
        # Fakültedeki tüm seçmeli dersler (ders başına tek satır — UNIQUE kısıt)
        cur.execute(
            "SELECT ders_id, bolum_id, ad FROM ders "
            "WHERE fakulte_id = ? AND DersTipi = 'Seçmeli'",
            (fak,),
        )
        secmeliler = cur.fetchall()

        for ders_id, bolum_id, ad in secmeliler:
            did = int(ders_id)
            if did in ders_donem:
                statu = 1                       # müfredatta
                donem = ders_donem[did]         # müfredattaki dönemi
            else:
                statu = 0                       # havuzda (aday)
                donem = "Guz"                   # varsayılan
            cur.execute(
                "INSERT INTO havuz "
                "(ders_id, yil, fakulte_id, bolum_id, statu, sayac, "
                "donem, ders_adi) VALUES (?, ?, ?, ?, ?, 0, ?, ?)",
                (str(ders_id), YIL, fak, bolum_id, statu, donem, ad),
            )
            toplam += 1
        print(f"   Fakulte {fak}: {len(secmeliler)} secmeli ders islendi")

    conn.commit()
    print(f"3) Toplam {toplam} havuz satiri olusturuldu")

    # Doğrulama
    print("\n=== DOGRULAMA ===")
    cur.execute("SELECT yil, COUNT(*) FROM havuz GROUP BY yil")
    print("havuz yil:", cur.fetchall())
    cur.execute("SELECT DISTINCT donem FROM havuz")
    print("havuz donem:", [r[0] for r in cur.fetchall()])
    cur.execute("SELECT statu, COUNT(*) FROM havuz GROUP BY statu")
    print("havuz statu (1=mufredat, 0=havuz):", cur.fetchall())
    # Ornek: BMB (fakulte 2) Guz mufredattakiler
    cur.execute(
        "SELECT d.kod, d.ad, h.statu FROM havuz h JOIN ders d ON d.ders_id=h.ders_id "
        "WHERE h.fakulte_id=2 AND h.donem='Guz' AND h.statu=1 LIMIT 8"
    )
    print("Ornek fakulte=2 Guz mufredat (statu=1):")
    for r in cur.fetchall():
        print("  ", r)
    conn.close()
    print("\nTAMAMLANDI.")


if __name__ == "__main__":
    main()
