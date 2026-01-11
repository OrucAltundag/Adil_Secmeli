# app/services/ai_engine.py

import pandas as pd
import numpy as np
from sklearn.model_selection import cross_val_score, KFold
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.tree import DecisionTreeClassifier
from sqlalchemy.orm import Session
from sqlalchemy import text
import random

class AIEngine:
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_training_data(self):
        """
        Veritabanından yapay zeka için gerekli veriyi çeker ve hazırlar.
        Hedefimiz: Bir öğrencinin bir dersteki başarısını tahmin etmek.
        
        Girdiler (X):
        1. Ders Zorluğu: O dersin genel başarı oranı (veritabanından)
        2. Öğrenci Başarısı: Öğrencinin potansiyeli (simüle edilmiş)
        
        Çıktı (y):
        1. Not (Regresyon için)
        2. Geçti/Kaldı (Sınıflandırma için)
        """
        
        # 1. SQL ile Ham Veriyi Çek
        # Not: 'p.ortalama_not' yerine 'p.basari_orani' kullanıyoruz (Tablo yapısına uygun)
        
        sorgu = text("""
            SELECT 
                k.ogr_id,
                k.ders_id,
                k.durum,     -- Hedef (Geçti/Kaldı)
                p.basari_orani as ders_zorlugu, -- Girdi 1
                50 as ogr_basari -- Girdi 2 (Başlangıç değeri, aşağıda rastgele dolduracağız)
            FROM kayit k
            JOIN performans p ON k.ders_id = p.ders_id
            WHERE k.durum IN ('Geçti', 'Kaldı')
            LIMIT 2000;
        """)
        
        # Veritabanı sonucunu al
        veritabani_sonucu = self.db.execute(sorgu).fetchall()
        
        if not veritabani_sonucu:
            return None, None, None

        # Veriyi DataFrame'e (Tabloya) çevir
        veri_tablosu = pd.DataFrame(veritabani_sonucu, columns=['ogr_id', 'ders_id', 'durum', 'ders_zorlugu', 'ogr_basari'])
        
        # VERİ ZENGİNLEŞTİRME (Feature Engineering)
        
        # 1. Sınıflandırma Hedefi (y_sinif): Geçti=1, Kaldı=0
        veri_tablosu['y_sinif'] = veri_tablosu['durum'].apply(lambda x: 1 if x == 'Geçti' else 0)
        
        # 2. Regresyon Hedefi (y_not): Not tahmini için rastgele not üretimi
        def not_uret(durum):
            if durum == 'Geçti': return random.randint(50, 100)
            else: return random.randint(0, 49)
            
        veri_tablosu['y_not'] = veri_tablosu['durum'].apply(not_uret)
        
        # 3. Girdi Zenginleştirme: Öğrenci başarısını biraz çeşitlendirelim
        # (Gerçek veride transkript ortalaması olurdu, burada 40-90 arası rastgele veriyoruz)
        veri_tablosu['ogr_basari'] = np.random.randint(40, 90, veri_tablosu.shape[0])
        
        # Model Girdilerini (X) ve Hedeflerini (y) Ayır
        Girdiler = veri_tablosu[['ders_zorlugu', 'ogr_basari']].values
        y_siniflandirma = veri_tablosu['y_sinif'].values
        y_regresyon = veri_tablosu['y_not'].values
        
        return Girdiler, y_siniflandirma, y_regresyon

    def run_kfold_test(self, algorithm_type="rf", k=5):
        """
        Seçilen algoritmaya göre K-Katlı (K-Fold) doğrulama testi yapar.
        İsimler main.py ile uyumlu kalmalıdır.
        """
        # Veriyi hazırla
        X, y_sinif, y_not = self.get_training_data()
        
        if X is None:
            return "Veri bulunamadı. Lütfen önce MOCK (Sahte) veri üretimini çalıştırın."
        
        model = None
        hedef_y = None
        puanlama_metriki = ""
        gorev_adi = ""
        
        # --- ALGORİTMA AYARLARI ---
        if algorithm_type == "lr":
            # Lineer Regresyon (Sayı/Not Tahmini)
            model = LinearRegression()
            hedef_y = y_not
            puanlama_metriki = "neg_mean_absolute_error" # Hata payı (Negatif döner)
            gorev_adi = "Lineer Regresyon (Not Tahmini)"
            
        elif algorithm_type == "dt":
            # Karar Ağacı (Geçti/Kaldı Tahmini)
            model = DecisionTreeClassifier(max_depth=5) # Ağaç çok derinleşmesin
            hedef_y = y_sinif
            puanlama_metriki = "accuracy" # Doğruluk oranı
            gorev_adi = "Karar Ağacı (Geçme/Kalma Tahmini)"
            
        elif algorithm_type == "rf":
            # Random Forest (Geçti/Kaldı Tahmini - Daha güçlü)
            model = RandomForestClassifier(n_estimators=100, max_depth=5)
            hedef_y = y_sinif
            puanlama_metriki = "accuracy"
            gorev_adi = "Random Forest (Geçme/Kalma Tahmini)"
            
        # --- K-FOLD (ÇAPRAZ DOĞRULAMA) ÇALIŞTIRMA ---
        try:
            # Veriyi k parçaya bölüp test eden yapı
            k_katli_dogrulama = KFold(n_splits=k, shuffle=True, random_state=42)
            
            # Modeli eğit ve test et
            skorlar = cross_val_score(model, X, hedef_y, cv=k_katli_dogrulama, scoring=puanlama_metriki)
            
            # Sonuç Mesajını Oluştur
            sonuc_mesaji = f"=== {gorev_adi} ===\n"
            sonuc_mesaji += f"K-Fold Değeri (k): {k}\n"
            sonuc_mesaji += f"Eğitim Verisi Sayısı: {len(X)}\n\n"
            
            if puanlama_metriki == "neg_mean_absolute_error":
                # Hata skoru negatif döner, pozitife çevirip gösterelim
                mae_skorlari = -skorlar
                ortalama_hata = mae_skorlari.mean()
                sonuc_mesaji += f"Ortalama Hata Payı (MAE): {ortalama_hata:.2f} Puan\n"
                sonuc_mesaji += "(Yani sistem öğrencinin notunu +/- {:.0f} puan sapmayla biliyor)\n".format(ortalama_hata)
            else:
                # Doğruluk (Accuracy) skoru
                ortalama_dogruluk = skorlar.mean() * 100
                sonuc_mesaji += f"Ortalama Doğruluk (Accuracy): %{ortalama_dogruluk:.2f}\n"
                
            # Skorları temizle ve listele
            temiz_skorlar = [round(float(s), 3) if s > 0 else round(float(-s), 3) for s in skorlar]
            sonuc_mesaji += f"\nHer Turun Sonuçları:\n{temiz_skorlar}"
            
            return sonuc_mesaji
            
        except Exception as hata:
            return f"Yapay Zeka Motoru Hatası: {str(hata)}"