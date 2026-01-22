import sqlite3
import pandas as pd

def kontrol_et():
    conn = sqlite3.connect("data/adil_secmeli.db")
    cursor = conn.cursor()
    
    print("\n--- 1. 2023 YILI MÜFREDATINDAKİ DERSLER ---")
    cursor.execute("""
        SELECT d.ad, h.skor 
        FROM mufredat m
        JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
        JOIN ders d ON md.ders_id = d.ders_id
        LEFT JOIN havuz h ON d.ders_id = h.ders_id AND h.yil = 2023
        WHERE m.akademik_yil = 2023
    """)
    rows = cursor.fetchall()
    if not rows:
        print("❌ 2023 Müfredatı BOŞ görünüyor!")
    else:
        for r in rows:
            print(f"✅ Müfredatta: {r[0]} (Skor: {r[1]})")

    print("\n--- 2. 2023 HAVUZ DURUMU (Statüler) ---")
    cursor.execute("""
        SELECT d.ad, h.statu, h.skor 
        FROM havuz h
        JOIN ders d ON h.ders_id = d.ders_id
        WHERE h.yil = 2023
        ORDER BY h.skor DESC
        LIMIT 10
    """)
    rows = cursor.fetchall()
    for r in rows:
        durum = "🟢 SEÇİLDİ" if r[1] == 1 else ("🔴 ELENDİ/YEDEK" if r[1] <= 0 else "❓")
        print(f"{durum} : {r[0]} (Puan: {r[2]})")

    conn.close()

if __name__ == "__main__":
    kontrol_et()