from models import DersDinlendirme, SessionLocal
from datetime import datetime

db = SessionLocal()

# Örnek dinlendirme ekle
kayit = DersDinlendirme(
    ders_id=1,
    yil=datetime.now().year,
    bekleme_suresi=1,
    aktif=False,
    aciklama="Katılım azlığı nedeniyle dinlendirme alındı."
)
db.add(kayit)
db.commit()
db.close()

print("Ders dinlendirme kaydı eklendi.")
