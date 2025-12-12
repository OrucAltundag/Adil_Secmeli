# app/services/calculation.py
import math
import pandas as pd

class DecisionEngine:
    def __init__(self):
        self.logs = []  # Adım adım işlemleri buraya kaydedeceğiz

    def log(self, message):
        """Log listesine mesaj ekler."""
        self.logs.append(message)

    def run_ahp(self):
        """
        AHP (Analitik Hiyerarşi Süreci) ile Ağırlık Hesaplama
        Sunumundaki matris referans alınmıştır.
        Kriterler: B (Başarı), P (Popülerlik), A (Anket)
        """
        self.logs.clear()
        self.log("=== 1. AHP İLE AĞIRLIK BELİRLEME BAŞLADI ===")
        
        # 1. Karşılaştırma Matrisi (Sunumdan)
        # B=Başarı, P=Popülerlik, A=Anket Birbirlerine göre ne kadar önemli olduklarına bakıyoruz.
        criteria = ['B (Performans)', 'P (Popülerlik)', 'A (Anket)']
        matrix = [
            [1.0,    3.0,    4.0],  # B satırı
            [1/3,    1.0,    2.0],  # P satırı
            [1/4,    1/2,    1.0]   # A satırı
        ]

            # B, P’ye göre 3 kat daha önemli
            # B, A’ya göre 4 kat daha önemli
            # P, A’ya göre 2 kat daha önemli
        
        self.log(f"Adım 1: İkili Karşılaştırma Matrisi Oluşturuldu:\n{criteria}")
        for row in matrix:
            self.log(f"   {[round(x, 2) for x in row]}")

        # 2. Sütun Toplamları
        col_sums = [0, 0, 0]
        for i in range(3):
            col_sums[i] = sum(row[i] for row in matrix)
        
        self.log(f"\nAdım 2: Sütun Toplamları Hesaplandı:\n   {['{:.2f}'.format(x) for x in col_sums]}")

        # 3. Normalizasyon Matrisi ve Ağırlıklar
        weights = []
        self.log("\nAdım 3: Normalizasyon ve Ağırlık (Satır Ortalaması):")
        
        for r_idx, row in enumerate(matrix):
            # Her elemanı kendi sütun toplamına böl
            norm_row = [row[c_idx] / col_sums[c_idx] for c_idx in range(3)]
            # Satır ortalamasını al (Ağırlık)
            weight = sum(norm_row) / 3
            weights.append(weight)
            
            self.log(f"   Kriter {criteria[r_idx]}: {norm_row} -> Ağırlık: {weight:.4f}")

        self.log(f"\nSONUÇ AĞIRLIKLAR (W):")
        self.log(f"   w_Basari: {weights[0]:.4f}")
        self.log(f"   w_Populerlik: {weights[1]:.4f}")
        self.log(f"   w_Anket: {weights[2]:.4f}")
        
        return weights

    def run_topsis(self, df_data, weights):
        """
        TOPSIS ile Sıralama
        df_data: DataFrame (ders_adi, basari, populerlik, anket_puani)
        """
        self.log("\n=== 2. TOPSIS İLE SIRALAMA BAŞLADI ===")
        
        if df_data.empty:
            self.log("HATA: Hesaplanacak veri bulunamadı.")
            return pd.DataFrame()

        # Veri seti özeti
        self.log(f"İşlenecek Ders Sayısı: {len(df_data)}")
        
        # 1. Vektör Normalizasyonu
        # Formül: r_ij = x_ij / sqrt(sum(x_ij^2))
        self.log("\nAdım 1: Vektör Normalizasyonu Yapılıyor...")
        
        # Kareler toplamının karekökü (Payda)
        denominators = {}
        for col in ['basari', 'populerlik', 'anket']:
            sq_sum = sum(x**2 for x in df_data[col])
            denominators[col] = math.sqrt(sq_sum) if sq_sum > 0 else 1
            
        # Normalize Tablo
        norm_data = []
        for _, row in df_data.iterrows():
            norm_row = {
                'ders': row['ders'],
                'n_basari': row['basari'] / denominators['basari'],
                'n_pop': row['populerlik'] / denominators['populerlik'],
                'n_anket': row['anket'] / denominators['anket']
            }
            norm_data.append(norm_row)
        
        # 2. Ağırlıklı Normalize Matris (v_ij = w_j * r_ij)
        self.log("\nAdım 2: Ağırlıklı Normalize Matris Hesaplanıyor...")
        weighted_data = []
        for row in norm_data:
            w_row = {
                'ders': row['ders'],
                'v_basari': row['n_basari'] * weights[0],
                'v_pop': row['n_pop'] * weights[1],
                'v_anket': row['n_anket'] * weights[2]
            }
            weighted_data.append(w_row)

        # 3. İdeal (A*) ve Negatif İdeal (A-) Çözümler
        # Başarı, Popülerlik, Anket -> Hepsi "Benefit" (Daha çok olması iyi)
        v_basari_vals = [x['v_basari'] for x in weighted_data]
        v_pop_vals = [x['v_pop'] for x in weighted_data]
        v_anket_vals = [x['v_anket'] for x in weighted_data]

        ideal_best = [max(v_basari_vals), max(v_pop_vals), max(v_anket_vals)]
        ideal_worst = [min(v_basari_vals), min(v_pop_vals), min(v_anket_vals)]
        
        self.log(f"\nAdım 3: İdeal Çözümler Belirlendi:")
        self.log(f"   Pozitif İdeal (A*): {['{:.4f}'.format(x) for x in ideal_best]}")
        self.log(f"   Negatif İdeal (A-): {['{:.4f}'.format(x) for x in ideal_worst]}")

        # 4. Uzaklıkların Hesaplanması ve Skor (C*)
        results = []
        self.log("\nAdım 4 & 5: Uzaklıklar ve Yakınlık Katsayısı (Skor) Hesaplanıyor...")
        
        for i, row in enumerate(weighted_data):
            # S* (Pozitif İdeale Uzaklık)
            s_best = math.sqrt(
                (row['v_basari'] - ideal_best[0])**2 +
                (row['v_pop'] - ideal_best[1])**2 +
                (row['v_anket'] - ideal_best[2])**2
            )
            # S- (Negatif İdeale Uzaklık)
            s_worst = math.sqrt(
                (row['v_basari'] - ideal_worst[0])**2 +
                (row['v_pop'] - ideal_worst[1])**2 +
                (row['v_anket'] - ideal_worst[2])**2
            )
            
            # C* Skor = S- / (S* + S-)
            if (s_best + s_worst) == 0:
                score = 0
            else:
                score = s_worst / (s_best + s_worst)
            
            results.append({
                'Ders': row['ders'],
                'AHP_TOPSIS_Skor': round(score, 4),
                'S+': round(s_best, 4),
                'S-': round(s_worst, 4)
            })
            
            # İlk 3 dersin detayını logla (Hepsini yazarsak ekran taşar)
            if i < 3:
                self.log(f"   -> {row['ders']}: S+={s_best:.4f}, S-={s_worst:.4f} => Skor={score:.4f}")

        # Sonuçları DataFrame yap ve sırala
        df_result = pd.DataFrame(results).sort_values(by='AHP_TOPSIS_Skor', ascending=False)
        self.log(f"\n=== İŞLEM TAMAMLANDI. {len(df_result)} ders puanlandı. ===")
        
        return df_result, self.logs
    


    def calculate_historical_trend(self, history_data):
        """
        Geçmiş 3 yılın verisini ağırlıklı ortalama ile tek puana indirger.
        Girdi (history_data): [{'yil': 2024, 'oran': 0.8}, {'yil': 2023, 'oran': 0.4}, ...]
        """
        if not history_data:
            return 0.5 # Veri yoksa nötr puan
            
        # Yıla göre tersten sırala (En yeni en başa)
        sorted_data = sorted(history_data, key=lambda x: x['yil'], reverse=True)
        
        # Ağırlıklar: [En Yeni, Orta, En Eski] -> %50, %30, %20
        weights = [0.50, 0.30, 0.20]
        
        weighted_score = 0
        total_weight = 0
        
        log_msg = "   Tarihsel Analiz: "
        
        for i, record in enumerate(sorted_data):
            if i >= 3: break # Sadece son 3 yıl
            
            w = weights[i]
            val = record['oran']
            weighted_score += val * w
            total_weight += w
            
            log_msg += f"[{record['yil']}: {val:.2f} (x{w})]"
            
        # Eğer veri 3 yıldan azsa (mesela yeni açılan ders), ağırlığı normalize et
        if total_weight > 0:
            final_score = weighted_score / total_weight
        else:
            final_score = 0
            
        return final_score, f"{log_msg} => Trend Puanı: {final_score:.4f}"