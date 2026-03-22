# -*- coding: utf-8 -*-
# =============================================================================
# app/tests/reset_counters.py — Sayaç sıfırlama
# =============================================================================
# Havuz tablosundaki sayaç alanını toplu olarak sıfırlayan yardımcı betik.
# =============================================================================

import sqlite3

db_path = "data/adil_secmeli.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# TÜM SAYAÇLARI SIFIRLA
cursor.execute("UPDATE havuz SET sayac = 0")
conn.commit()
conn.close()

print("✅ Tamamdır abi, tüm sayaçlar 0'landı.")