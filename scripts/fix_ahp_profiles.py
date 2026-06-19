# -*- coding: utf-8 -*-
"""
AHP profillerini temiz, tutarli duruma getir:
 - Coklu is_active=1 sorununu coz (tek aktif profil)
 - Bozuk encoding'li ('Varsay\\xeflan') adlari ASCII-guvenli yap
 - Kopya/gecersiz profilleri sil
 - Tek bir saglikli aktif profil birak
"""
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

DB = Path(__file__).parent.parent / "data" / "adil_secmeli.db"


def temiz_ad(s):
    """Mojibake ad -> ASCII-guvenli okunabilir ad."""
    if not s:
        return None
    # Bilinen bozuk kalip
    s = s.replace("\xef", "i").replace("�", "i")
    try:
        s.encode("ascii")
        return s
    except UnicodeEncodeError:
        # Turkce karakterleri ASCII'ye indir
        tr = {"ı": "i", "İ": "I", "ş": "s", "Ş": "S", "ğ": "g",
              "Ğ": "G", "ç": "c", "Ç": "C", "ö": "o", "Ö": "O",
              "ü": "u", "Ü": "U"}
        return "".join(str(tr.get(ch, ch)) for ch in s).encode(
            "ascii", "ignore"
        ).decode("ascii")


def main():
    yedek = str(DB) + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(str(DB), yedek)
    print(f"Yedek: {Path(yedek).name}")

    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()

    cur.execute(
        "SELECT id, profile_name, name, status, is_active, consistency_ratio "
        "FROM ahp_weight_profiles ORDER BY id"
    )
    rows = cur.fetchall()
    print(f"\nMevcut {len(rows)} profil:")
    for r in rows:
        print(f"  id={r[0]} name={r[1]!r} status={r[3]} active={r[4]} cr={r[5]}")

    if not rows:
        print("Profil yok — varsayilan olusturuluyor.")
        cur.execute(
            "INSERT INTO ahp_weight_profiles "
            "(profile_name, name, scope_type, version, status, is_active, "
            "consistency_ratio, notes) "
            "VALUES ('Varsayilan Global AHP Profili', "
            "'Varsayilan Global AHP Profili', 'global', 1, 'active', 1, 0.0, "
            "'Sistem tarafindan olusturulan varsayilan AHP profili.')"
        )
        conn.commit()
        print("Varsayilan profil olusturuldu.")
        conn.close()
        return

    # Tutulacak profil: tutarli (cr<=0.10) ve cr>0 olan ilk profil,
    # yoksa ilk profil. (Gercek hesaplanmis matris tercih edilir.)
    def skor(r):
        cr = r[5] if r[5] is not None else 1.0
        gercek_matris = 1 if (cr and cr > 0) else 0
        tutarli = 1 if (cr is not None and cr <= 0.10) else 0
        return (gercek_matris, tutarli, -r[0])

    tutulacak = sorted(rows, key=skor, reverse=True)[0]
    keep_id = tutulacak[0]
    yeni_ad = temiz_ad(tutulacak[1] or tutulacak[2]) or "Varsayilan Global AHP Profili"
    print(f"\nTutulacak: id={keep_id} -> ad '{yeni_ad}'")

    # Digerlerini sil
    for r in rows:
        if r[0] == keep_id:
            continue
        for sql in (
            "DELETE FROM ahp_profile_approval_logs WHERE profile_id=?",
            "DELETE FROM ahp_sensitivity_results WHERE ahp_profile_id=?",
            "UPDATE ahp_weight_profiles SET parent_profile_id=NULL WHERE parent_profile_id=?",
            "UPDATE ahp_weight_profiles SET superseded_by_profile_id=NULL WHERE superseded_by_profile_id=?",
            "DELETE FROM ahp_weight_profiles WHERE id=?",
        ):
            try:
                cur.execute(sql, (r[0],))
            except sqlite3.OperationalError:
                pass
        print(f"  silindi: id={r[0]}")

    # Tutulan profili temizle: tek aktif, ASCII ad, status=active
    cur.execute(
        "UPDATE ahp_weight_profiles SET profile_name=?, name=?, "
        "status='active', is_active=1 WHERE id=?",
        (yeni_ad, yeni_ad, keep_id),
    )
    # Baska aktif kalmasin
    cur.execute(
        "UPDATE ahp_weight_profiles SET is_active=0 WHERE id != ?", (keep_id,)
    )
    conn.commit()

    print("\n=== SONUC ===")
    cur.execute(
        "SELECT id, profile_name, status, is_active, consistency_ratio "
        "FROM ahp_weight_profiles"
    )
    for r in cur.fetchall():
        print(f"  id={r[0]} name={r[1]!r} status={r[2]} active={r[3]} cr={r[4]}")
    conn.close()
    print("\nTAMAMLANDI — tek temiz aktif profil.")


if __name__ == "__main__":
    main()
