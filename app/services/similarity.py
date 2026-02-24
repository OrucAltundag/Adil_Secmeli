# app/services/similarity.py
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session
from app.db.models import Ders

# Türkçe stop-words (gereksiz kelimeleri filtrele)
TURKCE_STOP_WORDS = {
    "ve", "veya", "ile", "için", "bir", "bu", "şu", "o", "da", "de", "ta", "te",
    "mi", "mu", "mü", "mı", "ın", "in", "un", "ün", "dan", "den", "tan", "ten",
    "na", "ne", "ni", "nu", "nü", "lar", "ler", "dır", "dir", "dur", "dür",
    "olarak", "gibi", "kadar", "daha", "en", "çok", "az", "ise", "ama", "fakat",
    "ancak", "yalnız", "sadece", "hem", "ya", "yani", "örneğin", "göre", "üzere",
    "doğru", "karşı", "sonra", "önce", "içinde", "dışında", "üzerinde", "altında",
}

class SimilarityEngine:
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_related_courses(self, target_course_id, top_n=10):
        """
        TF-IDF ve Cosine Similarity kullanarak benzer dersleri bulur.
        """
        # 1. Tüm dersleri ve içeriklerini çek
        # (Gerçek hayatta sadece aynı fakülteyi çekmek performansı artırır)
        dersler = self.db.query(Ders.ders_id, Ders.ad, Ders.bilgi).all()
        
        if not dersler:
            return [], None

        # DataFrame'e çevir
        df = pd.DataFrame(dersler, columns=['id', 'ad', 'icerik'])
        
        # Hedef dersi bul
        target_course = df[df['id'] == target_course_id]
        if target_course.empty:
            return [], None
            
        target_index = target_course.index[0]

        # 2. NLP İşlemi: Stop-words temizleme + TF-IDF
        df['icerik'] = df['icerik'].fillna("").astype(str)

        def _remove_stopwords(text):
            words = text.lower().split()
            return " ".join(w for w in words if w not in TURKCE_STOP_WORDS and len(w) > 1)

        df['icerik'] = df['icerik'].apply(_remove_stopwords)
        tfidf = TfidfVectorizer(max_features=500, stop_words=list(TURKCE_STOP_WORDS))
        
        tfidf_matrix = tfidf.fit_transform(df['icerik'])

        # 3. Benzerlik Hesapla (Cosine Similarity)
        # Hedef dersin vektörü ile diğer hepsinin vektörünü çarp
        cosine_sim = cosine_similarity(tfidf_matrix[target_index], tfidf_matrix)

        # 4. Sonuçları Sırala
        similarity_scores = list(enumerate(cosine_sim[0]))
        
        # Puana göre tersten sırala (En yüksek puan en başa)
        # Kendisini (1.0 puan) listeden çıkarmak için [1:] yapıyoruz
        sorted_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)[1:top_n+1]

        results = []
        graph_data = [] # Ağaç çizimi için veri (Source, Target, Weight)

        target_name = target_course.iloc[0]['ad']

        for i, score in sorted_scores:
            related_course_name = df.iloc[i]['ad']
            
            # Sonuç listesi için
            results.append({
                "ders": related_course_name,
                "skor": score
            })
            
            # Grafik çizimi için (Ağaç yapısı)
            # Sadece anlamlı ilişkileri çiz (Örn: %10 üzeri benzerlik)
            if score > 0.1:
                graph_data.append((target_name, related_course_name, score))

        return results, graph_data