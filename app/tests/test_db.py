# =============================================================================
# app/tests/test_db.py — Veritabanı Bağlantı ve Temel Okuma Testi
# =============================================================================
# Bu test:
# - config.json veya varsayılan DB yolundan veritabanına bağlanır
# - Raw SQLite ile havuz/ders tablolarından okuma yapar (ORM şemasından bağımsız)
# =============================================================================

import json
import os
import sqlite3
import sys

# Proje kökünü path'e ekle
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

os.chdir(_root)


def _get_db_path() -> str:
    """config.json'dan veya varsayılandan DB yolunu al."""
    default = os.path.join(_root, "data", "adil_secmeli.db")
    cfg = os.path.join(_root, "config.json")
    if os.path.exists(cfg):
        try:
            with open(cfg, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("db_path", default)
        except Exception:
            pass
    for p in (default, os.path.join(_root, "adil_secmeli.db"), "./adil_secmeli.db"):
        if p and os.path.exists(p):
            return p
    return default


def test_db_connection():
    """Veritabanı bağlantısı ve temel okuma testi (raw SQLite)."""
    db_path = _get_db_path()
    if not os.path.exists(db_path):
        raise AssertionError(f"DB dosyası bulunamadı: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        # havuz tablosu var mı?
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='havuz'")
        if not cur.fetchone():
            raise AssertionError("havuz tablosu yok")

        cur.execute("SELECT COUNT(*) FROM havuz")
        count = cur.fetchone()[0]
        assert count >= 0, "Havuz okunamadı"

        # ders tablosu da kontrol
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ders'")
        if not cur.fetchone():
            raise AssertionError("ders tablosu yok")
    finally:
        conn.close()


if __name__ == "__main__":
    test_db_connection()
    print("✅ DB bağlantı testi geçti.")
