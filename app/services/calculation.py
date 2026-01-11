import math
import pandas as pd

class KararMotoru:
    def __init__(self, havuz_verisi):
        self.kayitlar = []
        # havuz_verisi: Tüm derslerin tutulduğu ana liste/sözlük
        self.havuz = havuz_verisi 
        self.mevcut_yil = 2022

    def kayit_ekle(self, mesaj):
        """İşlem loglarını tutar."""
        self.kayitlar.append(mesaj)

    def gecmis_trend_hesapla(self, gecmis_veri):
        """
        Geçmiş 3 yılın verisini ağırlıklı ortalama ile 'Trend Skoru'na dönüştürür.
        Girdi: [{'yil': 2024, 'oran': 0.8}, {'yil': 2023, 'oran': 0.4}, ...]
        """
        if not gecmis_veri:
            return 0.5, "Veri Yok (Nötr)" 
            
        # Yıla göre tersten sırala (En yeni en başa: 2024, 2023, 2022...)
        sirali_veri = sorted(gecmis_veri, key=lambda x: x['yil'], reverse=True)
        
        # Ağırlıklar: [En Yeni (%50), Orta (%30), En Eski (%20)]
        agirliklar = [0.50, 0.30, 0.20]
        
        agirlikli_puan = 0
        toplam_agirlik = 0
        log_mesaji = ""
        
        for i, kayit in enumerate(sirali_veri):
            if i >= 3: break
            agirlik = agirliklar[i]
            deger = kayit['oran']
            
            agirlikli_puan += deger * agirlik
            toplam_agirlik += agirlik
            log_mesaji += f"[{kayit['yil']}: {deger:.2f} x{agirlik}] "
            
        if toplam_agirlik > 0:
            nihai_puan = agirlikli_puan / toplam_agirlik
        else:
            nihai_puan = 0
            
        return nihai_puan, f"Trend: {log_mesaji} = {nihai_puan:.4f}"

    def ahp_calistir(self):
        """
        GÜNCELLENMİŞ AHP (4 KRİTERLİ)
        Kriterler: 
        1. Performans (B) - En Önemli
        2. Trend (T) - Performansa yakın, gelecek projeksiyonu
        3. Popülerlik (P) - Öğrenci talebi
        4. Anket (A) - Öğrenci memnuniyeti
        """
        self.kayitlar.clear()
        self.kayit_ekle("=== AHP (4 KRİTER) BAŞLADI ===")
        
        # Kriterler: Performans, Trend, Popülerlik, Anket
        # kriterler = ['Performans', 'Trend', 'Popülerlik', 'Anket']
        
        # 4x4 Karşılaştırma Matrisi (Örnek Senaryo)
        # 1. Satır (Perf): Trend'den biraz, Pop'tan çok, Anketten çok daha önemli.
        matris = [
            [1.00, 2.00, 4.00, 5.00],  # Performans
            [0.50, 1.00, 3.00, 4.00],  # Trend (Perf'in yarısı kadar önemli)
            [0.25, 0.33, 1.00, 2.00],  # Popülerlik
            [0.20, 0.25, 0.50, 1.00]   # Anket
        ]

        # 2. Sütun Toplamları
        sutun_toplamlari = [0]*4
        for i in range(4):
            sutun_toplamlari[i] = sum(satir[i] for satir in matris)

        # 3. Ağırlık Hesaplama (Normalizasyon + Ortalamalar)
        agirliklar = []
        for satir in matris:
            normalize_satir = [satir[i] / sutun_toplamlari[i] for i in range(4)]
            agirliklar.append(sum(normalize_satir) / 4)

        self.kayit_ekle(f"Ağırlıklar: Perf={agirliklar[0]:.2f}, Trend={agirliklar[1]:.2f}, Pop={agirliklar[2]:.2f}, Anket={agirliklar[3]:.2f}")
        return agirliklar

    def topsis_calistir(self, df_veri, agirliklar):
        """
        GÜNCELLENMİŞ TOPSIS (4 SÜTUNLU)
        df_veri kolonları: ['ders', 'basari', 'trend', 'populerlik', 'anket']
        """
        self.kayit_ekle("\n=== TOPSIS (4 KRİTER) BAŞLADI ===")
        if df_veri.empty: return pd.DataFrame(), []

        # 1. Normalizasyon Paydaları (Karekökler toplamı)
        sutunlar = ['basari', 'trend', 'populerlik', 'anket']
        paydalar = {}
        for col in sutunlar:
            kareler_toplami = sum(x**2 for x in df_veri[col])
            paydalar[col] = math.sqrt(kareler_toplami) if kareler_toplami > 0 else 1

        # 2. Ağırlıklı Normalize Matris ve İdeal Çözümler
        agirlikli_veri = []
        
        # İdeal çözümleri (Min/Max) bulmak için listeler
        degerler = {c: [] for c in sutunlar}

        for _, satir in df_veri.iterrows():
            agirlikli_satir = {'ders': satir['ders']}
            for i, col in enumerate(sutunlar):
                # Formül: (Değer / Payda) * Ağırlık
                norm_deger = (satir[col] / paydalar[col]) * agirliklar[i]
                agirlikli_satir[col] = norm_deger
                degerler[col].append(norm_deger)
            agirlikli_veri.append(agirlikli_satir)

        # Hepsi "Fayda" (Benefit) kriteri olduğu için Max=İdeal, Min=Kötü
        ideal_en_iyi = {c: max(v) for c, v in degerler.items()}
        ideal_en_kotu = {c: min(v) for c, v in degerler.items()}

        # 3. Uzaklıklar ve Skor
        sonuclar = []
        for satir in agirlikli_veri:
            # S+ (İyiye Uzaklık)
            uzaklik_en_iyi = math.sqrt(sum((satir[c] - ideal_en_iyi[c])**2 for c in sutunlar))
            # S- (Kötüye Uzaklık)
            uzaklik_en_kotu = math.sqrt(sum((satir[c] - ideal_en_kotu[c])**2 for c in sutunlar))
            
            # C* Skor Hesaplama
            if (uzaklik_en_iyi + uzaklik_en_kotu) > 0:
                skor = uzaklik_en_kotu / (uzaklik_en_iyi + uzaklik_en_kotu)
            else:
                skor = 0
            
            sonuclar.append({
                'Ders': satir['ders'],
                'AHP_TOPSIS_Skor': skor,
                'S+': uzaklik_en_iyi,
                'S-': uzaklik_en_kotu
            })

        df_sonuc = pd.DataFrame(sonuclar).sort_values(by='AHP_TOPSIS_Skor', ascending=False)
        return df_sonuc, self.kayitlar

    def durumlari_guncelle(self, mevcut_mufredat_idleri, gelecek_mufredat_idleri):
        """
        mevcut_mufredat_idleri: Şu anki (biten) yılın ders ID listesi
        gelecek_mufredat_idleri: Puanı yetip bir sonraki yıla geçen ders ID listesi
        """
        kayitlar = [] # İşlem logları
        
        for ders in self.havuz:
            ders_id = ders['id']
            
            # DURUM 1: Ders müfredattaydı ama yeni listeye giremedi (Düştü)
            if ders_id in mevcut_mufredat_idleri and ders_id not in gelecek_mufredat_idleri:
                ders['sayac'] += 1 # Sayacı artır
                
                if ders['sayac'] >= 2:
                    ders['status'] = -1
                    kayitlar.append(f"{ders_id}: Başarısızlık limiti doldu. Status -> -1")
                else:
                    ders['status'] = 0
                    kayitlar.append(f"{ders_id}: Müfredattan düştü. Sayaç: {ders['sayac']}, Status -> 0")

            # DURUM 2: Ders yeni listeye seçildi (veya yerini korudu)
            elif ders_id in gelecek_mufredat_idleri:
                ders['status'] = 1
                # Not: Başarılı olursa sayacı sıfırlamak ister misin? 
                # Genelde "seri bozulduğu" için sayaç sıfırlanır, ama kuralda belirtilmediği için ellemedim.
                # ders['sayac'] = 0  <-- Opsiyonel: Başarılı olunca sicili temizle.
                kayitlar.append(f"{ders_id}: Müfredata seçildi/kaldı. Status -> 1")
                
            # DURUM 3: Ders zaten havuzdaydı ve seçilmedi
            else:
                # Status değişmez (0 veya -1 olarak kalır)
                pass
                
        return self.havuz, kayitlar