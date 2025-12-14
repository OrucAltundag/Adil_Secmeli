
import sys
import os

# Proje kök dizinini path'e ekle
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)


from app.services.similarity_engine import SimilarityEngine

DB_PATH = "data/adil_secmeli.db"

engine = SimilarityEngine(DB_PATH)

# 🔁 Buraya veritabanında VAR OLAN bir ders_id yaz
TEST_DERS_ID = 1  

engine.compute_and_save(TEST_DERS_ID, top_n=10)
results = engine.get_similar_courses(TEST_DERS_ID, top_n=10)


print(f"\n📘 Seçilen ders ID: {TEST_DERS_ID}")
print("🔗 En benzer dersler:\n")

for r in results:
    print(f"- {r['ders']}  →  skor: {r['skor']}")
