import sqlite3
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class SimilarityEngine:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def load_courses(self):
        conn = self._get_connection()

        query = """
        SELECT ders_id, ad, bilgi
        FROM ders
        WHERE bilgi IS NOT NULL
          AND LENGTH(bilgi) > 1
        """

        df = pd.read_sql_query(query, conn)
        conn.close()

        return df

    def compute_similarity(self):
        df = self.load_courses()

        if df.empty:
            raise ValueError("NLP için yeterli ders içeriği yok.")

        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words=None,     # TR stopwords birazdan eklenebilir
            max_features=5000,
            ngram_range=(1, 2)   # akademik metinler için önemli
        )

        tfidf_matrix = vectorizer.fit_transform(df["bilgi"])
        similarity_matrix = cosine_similarity(tfidf_matrix)

        return df.reset_index(drop=True), similarity_matrix

    def get_similar_courses(self, target_ders_id: int, top_n: int = 10):
        df, sim_matrix = self.compute_similarity()

        if target_ders_id not in df["ders_id"].values:
            raise ValueError(f"Ders ID bulunamadı: {target_ders_id}")

        idx = df.index[df["ders_id"] == target_ders_id][0]

        scores = list(enumerate(sim_matrix[idx]))
        scores = sorted(scores, key=lambda x: x[1], reverse=True)

        results = []
        for i, score in scores[1: top_n + 1]:
            results.append({
                "ders_id": int(df.iloc[i]["ders_id"]),
                "ders": df.iloc[i]["ad"],
                "skor": round(float(score), 4)
            })

        return results
    
    def compute_and_save(self, target_ders_id: int, top_n: int = 10):
        
        results = self.get_similar_courses(target_ders_id, top_n)

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Eski ilişkileri sil
        cur.execute(
            "DELETE FROM ders_iliski WHERE kaynak_ders_id = ?",
            (target_ders_id,)
        )

        # Yenilerini ekle
        for r in results:
            cur.execute(
                """
                INSERT OR REPLACE INTO ders_iliski
                (kaynak_ders_id, hedef_ders_id, skor)
                VALUES (?, ?, ?)
                """,
                (target_ders_id, r["ders_id"], r["skor"])
            )

        conn.commit()
        conn.close()

