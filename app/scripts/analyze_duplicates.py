"""Tekrarlayan dersleri analiz et."""
import json
import os
import sqlite3

base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(base)
cfg = json.load(open("config.json", encoding="utf-8")) if os.path.exists("config.json") else {}
path = cfg.get("db_path", "data/adil_secmeli.db")
if not os.path.exists(path):
    path = "data/adil_secmeli.db"

conn = sqlite3.connect(path)
cur = conn.cursor()

# ders_id iceren tablolar
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
tables = [r[0] for r in cur.fetchall()]
fk_tables = []
for t in tables:
    cur.execute(f"PRAGMA table_info({t})")
    cols = [r[1] for r in cur.fetchall()]
    if "ders_id" in cols:
        fk_tables.append(t)
print("ders_id referansı olan tablolar:", fk_tables)

# havuz ders_id tipi
cur.execute("PRAGMA table_info(havuz)")
havuz_cols = {r[1]: r[2] for r in cur.fetchall()}
print("havuz.ders_id tipi:", havuz_cols.get("ders_id", "yok"))

# Ayni isimde tekrar (sadece ad)
cur.execute("SELECT ad, COUNT(*), GROUP_CONCAT(ders_id) FROM ders GROUP BY ad HAVING COUNT(*) > 1")
dups_ad = cur.fetchall()
print("\nAyni isimde tekrar (ad ile):", len(dups_ad))
for r in dups_ad[:20]:
    print(f"  '{r[0]}': {r[1]} adet -> IDs: {r[2]}")

# Ayni ad+fakulte
cur.execute("""
    SELECT ad, COALESCE(fakulte_id,0), COUNT(*), GROUP_CONCAT(ders_id)
    FROM ders GROUP BY ad, COALESCE(fakulte_id,0) HAVING COUNT(*) > 1
""")
dups_af = cur.fetchall()
print("\nAyni ad+fakulte tekrar:", len(dups_af))

conn.close()
