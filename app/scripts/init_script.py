import pandas as pd

class DecisionEngine:
    def __init__(self, all_unique_course_ids):
        """
        Başlangıçta sistemdeki tüm tekil derslerin listesi verilir.
        Herkes 0 noktasından başlar.
        """
        self.havuz = {}
        for ders_id in all_unique_course_ids:
            self.havuz[ders_id] = {
                'id': ders_id,
                'status': 0, # Havuzda
                'sayac': 0,  # Hiç hata yapmadı
                'skor': 0    # Başarı puanı (Dönem geçirme sayısı)
            }
        self.logs = []

    def log(self, msg):
        self.logs.append(msg)

    def simulate_history(self, history_map):
        """
        Geçmiş yılları sırayla işleyerek bugünkü durumu oluşturur.
        history_map formatı: {2020: ['D1', 'D2'], 2021: ['D1', 'D3'], ...}
        """
        sorted_years = sorted(history_map.keys())
        self.log(f"--- Simülasyon Başlıyor: Yıllar {sorted_years} ---")

        # ÖNCE: İlk yılın (Örn: 2020) kurulumunu yap
        first_year = sorted_years[0]
        first_curriculum = history_map[first_year]
        
        for d_id in first_curriculum:
            if d_id in self.havuz:
                self.havuz[d_id]['status'] = 1
                self.havuz[d_id]['skor'] += 1 # İlk yıl primi
        
        self.log(f"[{first_year}] Kurulum tamamlandı. {len(first_curriculum)} ders aktif.")

        # SONRA: Yıllar arası geçişleri yap (2020->2021, 2021->2022)
        for i in range(len(sorted_years) - 1):
            current_y = sorted_years[i]
            next_y = sorted_years[i+1]
            
            curr_curr = history_map[current_y] # O yılki liste
            next_curr = history_map[next_y]    # Sonraki yılki liste
            
            self._apply_transition_rules(current_y, next_y, curr_curr, next_curr)

        return list(self.havuz.values())

    def _apply_transition_rules(self, year_from, year_to, current_ids, next_ids):
        """
        İki yıl arasındaki geçiş kurallarını uygular.
        """
        self.log(f"\n>> Geçiş: {year_from} -> {year_to}")
        
        for d_id, data in self.havuz.items():
            # 1. Müfredatta kalmaya devam eden veya yeni giren (BAŞARILI)
            if d_id in next_ids:
                data['status'] = 1
                data['skor'] += 1 # Başarılı geçen her yıl için +1 skor
                # Opsiyonel: Başarılı olunca sayaç sıfırlansın mı? 
                # data['sayac'] = 0 (Senin kuralında yoktu, kapalı tutuyorum)
                
            # 2. Müfredattaydı ama düştü (BAŞARISIZ)
            elif d_id in current_ids and d_id not in next_ids:
                data['sayac'] += 1
                if data['sayac'] >= 2:
                    data['status'] = -1
                    self.log(f"❌ {d_id}: Limit doldu! (Sayaç: 2) -> Status -1")
                else:
                    data['status'] = 0
                    self.log(f"⚠️ {d_id}: Müfredattan düştü. Sayaç -> {data['sayac']}")
            
            # 3. Zaten dışarıdaydı ve yine seçilmedi (ETKİSİZ)
            else:
                pass # Status değişmez (-1 ise -1 kalır, 0 ise 0 kalır)