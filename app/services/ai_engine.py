# app/services/ai_engine.py

import pandas as pd
import numpy as np
from sklearn.model_selection import cross_val_score, KFold
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.tree import DecisionTreeClassifier
from sqlalchemy.orm import Session
from sqlalchemy import text

class AIEngine:
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_training_data(self):
        """
        Veritabanından yapay zeka için gerekli veriyi çeker ve hazırlar.
        Hedefimiz: Bir öğrencinin bir dersteki başarısını tahmin etmek.
        
        Girdiler (X):
        1. Ders Zorluğu (Tahmini): O dersin genel başarı oranı
        2. Öğrenci Başarısı (Tahmini): Öğrencinin diğer derslerdeki ortalaması
        
        Çıktı (y):
        1. Not (Regresyon için)
        2. Geçti/Kaldı (Sınıflandırma için)
        """
        
        # 1. SQL ile Ham Veriyi Çek
        # Bu sorgu her kayıt için; Öğrenci ID, Ders ID, ve Notu getirir.
        # Ayrıca o dersin genel ortalamasını (Zorluk) ve öğrencinin genel ortalamasını (Potansiyel) hesaplarız.
        
        # Hız için limitli veri çekelim (ML eğitimi için 2000 satır yeterli)
        query = text("""
            SELECT 
                k.ogr_id,
                k.ders_id,
                k.durum,     -- Hedef (Geçti/Kaldı) - String
                p.ortalama_not as ders_zorlugu, -- Girdi 1 (Dersin Zorluğu)
                -- Not: Öğrenci başarısını SQL'de hesaplamak pahalıdır, Python'da yapacağız
                -- Şimdilik 'potansiyel' sütunu varsa onu kullanırız, yoksa rastgele atarız
                50 as ogr_basari -- Placeholder
            FROM kayit k
            JOIN performans p ON k.ders_id = p.ders_id
            WHERE k.durum IN ('Geçti', 'Kaldı')
            LIMIT 2000;
        """)
        
        result = self.db.execute(query).fetchall()
        
        if not result:
            return None, None, None

        # Veriyi DataFrame'e çevir
        df = pd.DataFrame(result, columns=['ogr_id', 'ders_id', 'durum', 'ders_zorlugu', 'ogr_basari'])
        
        # VERİ ZENGİNLEŞTİRME (Feature Engineering)
        # Öğrencinin başarısını simüle edelim (Gerçek hayatta transkriptten hesaplanırdı)
        # BigData scriptinde "potansiyel" diye bir şey üretmiştik, onu yansıtıyoruz
        # Burada notu olmayan kayıtlar için sentetik not üretimi yapıyoruz
        
        # Geçti/Kaldı -> 1/0 dönüşümü
        df['y_class'] = df['durum'].apply(lambda x: 1 if x == 'Geçti' else 0)
        
        # Regresyon için Not üretimi (Eğer veritabanında not sütunu yoksa)
        # Geçenler 50-100 arası, Kalanlar 0-49 arası rastgele dağıtılır
        import random
        def generate_grade(status):
            if status == 'Geçti': return random.randint(50, 100)
            else: return random.randint(0, 49)
            
        df['y_reg'] = df['durum'].apply(generate_grade)
        
        # Girdiler (X): [Ders Zorluğu, Öğrenci Başarısı]
        # Şu an öğrenci başarısı sabit 50 geldiği için modele biraz gürültü ekleyelim ki çalışsın
        df['ogr_basari'] = np.random.randint(40, 90, df.shape[0])
        
        X = df[['ders_zorlugu', 'ogr_basari']].values
        y_class = df['y_class'].values
        y_reg = df['y_reg'].values
        
        return X, y_class, y_reg

    def run_kfold_test(self, algorithm_type="rf", k=5):
        """
        Seçilen algoritmaya göre K-Fold testi yapar.
        """
        X, y_class, y_reg = self.get_training_data()
        
        if X is None:
            return "Veri bulunamadı. Lütfen önce MOCK veriyi oluşturun."
        
        model = None
        y = None
        scoring = ""
        task_name = ""
        
        # --- ALGORİTMA AYARLARI ---
        if algorithm_type == "lr":
            # Lineer Regresyon (Sayı Tahmini)
            model = LinearRegression()
            y = y_reg
            scoring = "neg_mean_absolute_error" # Hata payı (MAE)
            task_name = "Lineer Regresyon (Not Tahmini)"
            
        elif algorithm_type == "dt":
            # Karar Ağacı (Sınıflandırma)
            model = DecisionTreeClassifier(max_depth=5) # Aşırı öğrenmeyi engellemek için derinlik sınırı
            y = y_class
            scoring = "accuracy" # Doğruluk
            task_name = "Karar Ağacı (Geçme/Kalma Tahmini)"
            
        elif algorithm_type == "rf":
            # Random Forest (Sınıflandırma)
            model = RandomForestClassifier(n_estimators=100, max_depth=5)
            y = y_class
            scoring = "accuracy"
            task_name = "Random Forest (Geçme/Kalma Tahmini)"
            
        # --- K-FOLD ÇALIŞTIRMA ---
        try:
            kf = KFold(n_splits=k, shuffle=True, random_state=42)
            
            # Cross Validation
            scores = cross_val_score(model, X, y, cv=kf, scoring=scoring)
            
            result_msg = f"=== {task_name} ===\n"
            result_msg += f"K-Fold Değeri (k): {k}\n"
            result_msg += f"Eğitim Verisi Sayısı: {len(X)}\n\n"
            
            if scoring == "neg_mean_absolute_error":
                # Hata skoru negatif döner, pozitife çevir
                mae_scores = -scores
                avg_mae = mae_scores.mean()
                result_msg += f"Ortalama Hata Payı (MAE): {avg_mae:.2f} Puan\n"
                result_msg += "(Yani sistem notu +/- {:.0f} puan hatayla biliyor)\n".format(avg_mae)
            else:
                # Accuracy skoru
                avg_acc = scores.mean() * 100
                result_msg += f"Ortalama Doğruluk (Accuracy): %{avg_acc:.2f}\n"
                
            # DÜZELTME: np.float64'ü normal float'a çeviriyoruz (float(s))
            clean_scores = [round(float(s), 3) if s > 0 else round(float(-s), 3) for s in scores]
            result_msg += f"\nHer Turun Sonuçları:\n{clean_scores}"
           
            
            return result_msg
            
        except Exception as e:
            return f"ML Motoru Hatası: {str(e)}"