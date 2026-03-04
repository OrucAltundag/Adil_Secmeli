# =============================================================================
# app/tests/test_db.py — Veritabanı Bağlantı ve Temel Model Testi
# =============================================================================
# Bu test:
# - SQLAlchemy SessionLocal ile veritabanı bağlantısını kontrol eder
# - Mevcut modellerden (Havuz) örnek okuma yapar
# =============================================================================

import os
import sys

# Proje kökünü path'e ekle
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

from app.db.database import SessionLocal
from app.db.models import Havuz


def test_db_connection():
    """Veritabanı bağlantısı ve temel okuma testi."""
    db = SessionLocal()
    try:
        count = db.query(Havuz).count()
        assert count >= 0, "Havuz tablosu okunamadı"
    except Exception as e:
        raise AssertionError(f"DB test hatası: {e}") from e
    finally:
        db.close()


if __name__ == "__main__":
    test_db_connection()
    print("✅ DB bağlantı testi geçti.")
