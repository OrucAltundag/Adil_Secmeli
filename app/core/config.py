import os

class Settings:
    PROJECT_NAME: str = "Adil Secmeli Ders Asistani"
    VERSION: str = "1.0.0"
    
    # Veritabanı Yolu (Otomatik olarak data klasörünü bulur)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DB_NAME = "adil_secmeli.db"
    DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'data', DB_NAME)}"

    # Algoritma Ağırlıkları (Varsayılan)
    WEIGHTS = {
        "performance": 0.5,
        "popularity": 0.3,
        "survey": 0.2
    }

settings = Settings()