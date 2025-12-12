from app.db.database import engine, Base
from app.db.models import * # Tüm modelleri yükle ki SQLAlchemy görsün

def init_db():
    print("Veritabanı tabloları oluşturuluyor...")
    Base.metadata.create_all(bind=engine)
    print("İşlem tamam! 'adil_secimli.db' dosyası oluşturuldu.")
    print("Oluşturulan Tablolar:")
    for table in Base.metadata.tables:
        print(f" - {table}")

if __name__ == "__main__":
    init_db()