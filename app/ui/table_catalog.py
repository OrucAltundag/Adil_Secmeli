# -*- coding: utf-8 -*-
"""
Veritabani tablo katalogu — Turkce gorunen ad + aciklama + kullanim bilgisi.

ONEMLI: Bu katalog yalnizca GORUNTULEME icindir. Fiziksel tablo adlari
(ders, performans, decision_runs ...) DEGISMEZ; tum SQL aynen calisir.
Tablo Goruntule sayfasi bu katalogu kullanarak listede Turkce ad gosterir ve
secili tablo icin "ne tutar / nerede kullanilir" bilgisini sunar.

Kayit yapisi:
    "fiziksel_ad": {
        "tr":    "Turkce Gorunen Ad",
        "desc":  "Tablonun ne tuttugu (1-2 cumle)",
        "usage": "Hangi sayfa/serviste, nasil kullanildigi",
        "grup":  "Kategori (gruplama/renk icin)",
    }

Katalogda olmayan tablolar icin `get_table_info` makul bir Turkce baslik ve
genel aciklama uretir (bilinmeyen tablo cokmeye yol acmaz).
"""
from __future__ import annotations

from typing import Any

# Kategori etiketleri
G_KAYNAK = "Kaynak Veri"
G_KRITER = "Kriter & Veri Kalitesi"
G_KARAR = "Karar Süreci"
G_AHP = "AHP & Ağırlık"
G_HAVUZ = "Havuz & Statü"
G_PLAN = "Dönem Planlama"
G_IMPORT = "Veri İçe Aktarım"
G_ML = "ML & Benchmark"
G_SISTEM = "Sistem & Güvenlik"

TABLE_CATALOG: dict[str, dict[str, str]] = {
    # ---- Kaynak veri ----
    "fakulte": {"tr": "Fakülteler", "grup": G_KAYNAK,
        "desc": "Üniversitedeki fakültelerin listesi (ad, kimlik).",
        "usage": "Tüm sayfalarda kapsam (fakülte) seçiminin temeli."},
    "bolum": {"tr": "Bölümler", "grup": G_KAYNAK,
        "desc": "Fakültelere bağlı bölümler.",
        "usage": "Kapsam seçimi ve müfredat ilişkilendirmesinde."},
    "ders": {"tr": "Dersler", "grup": G_KAYNAK,
        "desc": "Tüm derslerin ana kaydı (kod, ad, fakülte, bölüm, tür).",
        "usage": "Kriter, karar, planlama — her yerin merkez tablosu."},
    "mufredat": {"tr": "Müfredatlar", "grup": G_KAYNAK,
        "desc": "Yıl/dönem bazında fakülte-bölüm müfredat başlıkları.",
        "usage": "Zorunlu kriter kümesini ve karar kapsamını belirler."},
    "mufredat_ders": {"tr": "Müfredat–Ders Eşleşmesi", "grup": G_KAYNAK,
        "desc": "Hangi dersin hangi müfredatta olduğunu eşler.",
        "usage": "Veri Kalitesi'nde 'zorunlu ders' paydası buradan gelir."},
    "ders_iliski": {"tr": "Ders İlişkileri", "grup": G_KAYNAK,
        "desc": "Dersler arası benzerlik/ilişki kayıtları (NLP).",
        "usage": "Kriter & Havuz → Ders İlişkileri & Kurallar sayfası."},
    "ders_ogretim": {"tr": "Ders–Öğretim Üyesi", "grup": G_KAYNAK,
        "desc": "Dersi veren öğretim üyesi eşleşmeleri.",
        "usage": "Planlamada öğretim üyesi uygunluğu kontrolünde."},
    "ogretim_gorevlisi": {"tr": "Öğretim Görevlileri", "grup": G_KAYNAK,
        "desc": "Öğretim üyesi/görevlisi kayıtları.",
        "usage": "Dönem planlamada hoca yükü ve çakışma kontrolü."},
    "instructors": {"tr": "Öğretim Üyeleri (Planlama)", "grup": G_KAYNAK,
        "desc": "Planlama tarafının öğretim üyesi kayıtları.",
        "usage": "instructor_planning_service ile dönem atamada."},
    "okul": {"tr": "Okul/Kurum", "grup": G_KAYNAK,
        "desc": "Kurum düzeyi tanım kaydı.",
        "usage": "Genel kapsam/üst bilgi."},
    "ogrenci": {"tr": "Öğrenciler", "grup": G_KAYNAK,
        "desc": "Öğrenci ana kayıtları.",
        "usage": "Not/anket veri setlerinin öğrenci tarafı."},
    "ogrenci_not": {"tr": "Öğrenci Notları", "grup": G_KAYNAK,
        "desc": "Öğrenci-ders bazında not kayıtları.",
        "usage": "Kriterlerin (başarı/ortalama) ham kaynağı."},
    "ogrenci_engel": {"tr": "Öğrenci Engelleri", "grup": G_KAYNAK,
        "desc": "Öğrencinin ders alma engel/kısıt kayıtları.",
        "usage": "Seçim simülasyonu ve uygunluk kontrolünde."},
    "kayit": {"tr": "Ders Kayıtları", "grup": G_KAYNAK,
        "desc": "Öğrenci-ders kayıt (enrollment) kayıtları.",
        "usage": "Talep/doluluk ve popülerlik hesabında."},

    # ---- Kriter & veri kalitesi ----
    "ders_kriterleri": {"tr": "Ders Kriterleri", "grup": G_KRITER,
        "desc": "Ders bazında girilen kriter değerleri (toplam/geçen öğrenci, ortalama, kontenjan, kayıtlı, anket).",
        "usage": "Kriter Girdi sayfasında girilir; karar motorunun ana girdisi."},
    "performans": {"tr": "Performans Verileri", "grup": G_KRITER,
        "desc": "Ders-yıl bazında ortalama not ve başarı oranı.",
        "usage": "TOPSIS 'başarı' kriteri; kriter kaydıyla yazılır."},
    "populerlik": {"tr": "Popülerlik Verileri", "grup": G_KRITER,
        "desc": "Ders-yıl bazında talep, kontenjan ve doluluk oranı.",
        "usage": "TOPSIS 'popülerlik' kriteri ve açılabilirlik talep skoru."},
    "skor": {"tr": "Hesaplanan Skorlar", "grup": G_KRITER,
        "desc": "Ders bazında hesaplanmış toplam skor (skor_top).",
        "usage": "Algoritma çıktısı; planlama yedek skor kaynağı."},
    "anket_form": {"tr": "Anket Formları", "grup": G_KRITER,
        "desc": "Anket form tanımları.",
        "usage": "Anket toplama yapısının başlığı."},
    "anket_cevap": {"tr": "Anket Cevapları", "grup": G_KRITER,
        "desc": "Öğrencilerin anket cevap kayıtları.",
        "usage": "Anket sonuçlarının ham verisi."},
    "anket_sonuclari": {"tr": "Anket Sonuçları", "grup": G_KRITER,
        "desc": "Ders bazında anket/tercih oy sayıları.",
        "usage": "BİLGİ AMAÇLI kriter; zorunlu değil, olgunluğu düşürmez."},
    "criteria_value_sources": {"tr": "Kriter Değer Kaynakları", "grup": G_KRITER,
        "desc": "Her kriter değerinin nereden geldiği (elle/import/üretim).",
        "usage": "Veri izlenebilirliği ve denetim."},
    "criteria_validation_issues": {"tr": "Kriter Doğrulama Sorunları", "grup": G_KRITER,
        "desc": "Kriter verisindeki kritik/uyarı düzeyi doğrulama sorunları.",
        "usage": "Veri Kalitesi → Doğrulama Sorunları; hazırlık kapısı."},
    "criteria_missing_data_risks": {"tr": "Eksik Veri Riskleri", "grup": G_KRITER,
        "desc": "Eksik kriterlerin oluşturduğu risk kayıtları.",
        "usage": "Veri Kalitesi risk değerlendirmesi."},
    "missing_data_items": {"tr": "Eksik Veri Kalemleri", "grup": G_KRITER,
        "desc": "Hangi dersin hangi verisinin eksik olduğu.",
        "usage": "Eksik Veri Matrisi görünümü."},
    "data_coverage_reports": {"tr": "Kapsama Raporları", "grup": G_KRITER,
        "desc": "Kaydedilmiş veri kapsama özetleri.",
        "usage": "Veri Kalitesi ve karar çalıştırması anı snapshot'ı."},
    "data_readiness_assessments": {"tr": "Veri Hazırlık Değerlendirmeleri", "grup": G_KRITER,
        "desc": "Olgunluk/hazırlık skor kayıtları.",
        "usage": "Hazırlık Kontrolü ve karar kapısı."},
    "data_validation_issues": {"tr": "Veri Doğrulama Sorunları", "grup": G_KRITER,
        "desc": "Genel veri doğrulama sorun kayıtları.",
        "usage": "Veri kalitesi denetimi (fallback)."},
    "data_collection_priorities": {"tr": "Veri Toplama Öncelikleri", "grup": G_KRITER,
        "desc": "Hangi verinin öncelikle tamamlanması gerektiği.",
        "usage": "Eksik tamamlama planlaması."},
    "data_snapshots": {"tr": "Veri Anlık Görüntüleri", "grup": G_KRITER,
        "desc": "Belirli anlardaki veri durumu kopyaları.",
        "usage": "Karşılaştırma ve denetim."},
    "criteria_completion_history": {"tr": "Kriter Tamamlama Geçmişi", "grup": G_KRITER,
        "desc": "Kriter doluluğunun zamanla değişim kaydı.",
        "usage": "Gelişmiş Tamlık Paneli geçmişi."},
    "criteria_completion_matrix": {"tr": "Kriter Tamamlama Matrisi", "grup": G_KRITER,
        "desc": "Ders×kriter doluluk matrisi.",
        "usage": "Tamlık paneli görselleştirmesi."},
    "criteria_completion_overrides": {"tr": "Tamamlama İstisnaları", "grup": G_KRITER,
        "desc": "Eksik kritere rağmen onaylı istisna (override) talepleri.",
        "usage": "Hazırlık kapısında override akışı."},
    "criteria_completion_policies": {"tr": "Tamamlama Politikaları", "grup": G_KRITER,
        "desc": "Kriter tamamlama eşik/kural tanımları.",
        "usage": "Tamlık değerlendirme kuralları."},
    "criteria_completion_tasks": {"tr": "Tamamlama Görevleri", "grup": G_KRITER,
        "desc": "Eksiklerden üretilen yapılacak görevler.",
        "usage": "Kriter sayfası 'Görev Oluştur'."},
    "criteria_department_status": {"tr": "Bölüm Kriter Durumu", "grup": G_KRITER,
        "desc": "Bölüm bazında kriter tamamlanma durumu.",
        "usage": "Kapsam özeti."},
    "criteria_faculty_status": {"tr": "Fakülte Kriter Durumu", "grup": G_KRITER,
        "desc": "Fakülte bazında kriter tamamlanma durumu.",
        "usage": "Kapsam özeti."},

    # ---- Karar süreci ----
    "decision_runs": {"tr": "Karar Çalıştırmaları", "grup": G_KARAR,
        "desc": "Her resmi karar çalıştırmasının başlık kaydı (yıl, kapsam, AHP profili, politika, durum).",
        "usage": "Karar Merkezi → Çalıştırmalar; tüm karar çıktılarının kökü."},
    "course_decisions": {"tr": "Ders Kararları", "grup": G_KARAR,
        "desc": "Ders bazında karar (eski/önerilen/final statü, TOPSIS, açılabilirlik, gerekçe).",
        "usage": "Karar Merkezi → Ders Kararları & Önerilen Dersler."},
    "course_score_breakdowns": {"tr": "Skor Kırılımları", "grup": G_KARAR,
        "desc": "Dersin TOPSIS hesabının ham/normalize/ağırlıklı değerleri.",
        "usage": "Ders kararı detayında matematiksel açıklama."},
    "course_trend_analysis": {"tr": "Trend Analizleri", "grup": G_KARAR,
        "desc": "Dersin yıllar arası trend skoru ve etiketi.",
        "usage": "Karar gerekçesi ve trend kriteri."},
    "course_data_confidence": {"tr": "Veri Güveni", "grup": G_KARAR,
        "desc": "Ders kararının dayandığı verinin güven skoru.",
        "usage": "Hassas kararlar ve gate değerlendirmesi."},
    "course_decision_explanations": {"tr": "Karar Açıklamaları", "grup": G_KARAR,
        "desc": "Ders kararının insan-okur gerekçe metni.",
        "usage": "Ders Kararları detay panelinde."},
    "course_governance_flags": {"tr": "Yönetişim Bayrakları", "grup": G_KARAR,
        "desc": "Derse özel yönetişim/istisna işaretleri.",
        "usage": "Karar motorunda manuel onay tetikleyici."},
    "decision_criteria_definitions": {"tr": "Karar Kriter Tanımları", "grup": G_KARAR,
        "desc": "Kullanılabilir karar kriterlerinin tanım kaydı.",
        "usage": "AHP kriter listesi referansı."},
    "decision_policies": {"tr": "Karar Politikaları", "grup": G_KARAR,
        "desc": "Skoru statüye çeviren eşik politikaları (≥70 müfredat vb.).",
        "usage": "Karar Merkezi → Karar Politikaları."},
    "decision_sensitivity_results": {"tr": "Karar Hassasiyeti", "grup": G_KARAR,
        "desc": "Kararın eşik/ağırlık değişimine duyarlılığı.",
        "usage": "Hassas Kararlar sekmesi."},
    "decision_staleness_flags": {"tr": "Bayatlama Bayrakları", "grup": G_KARAR,
        "desc": "Veri/profil değişince kararın güncelliğini yitirdiği işareti.",
        "usage": "Yeniden çalıştırma uyarısı."},
    "decision_fairness_reports": {"tr": "Adalet Raporları", "grup": G_KARAR,
        "desc": "Karar çalıştırmasının bölüm/fakülte adalet dağılımı.",
        "usage": "Karar Merkezi → Adalet Raporu."},
    "fairness_metric_items": {"tr": "Adalet Metrik Kalemleri", "grup": G_KARAR,
        "desc": "Adalet raporunun alt metrik satırları.",
        "usage": "Adalet raporu detayı."},
    "low_confidence_decision_flags": {"tr": "Düşük Güven Bayrakları", "grup": G_KARAR,
        "desc": "Veri güveni düşük kararların işaretleri.",
        "usage": "Hassas kararların tespiti."},
    "post_decision_outcomes": {"tr": "Karar Sonrası Sonuçlar", "grup": G_KARAR,
        "desc": "Kararların sonradan gözlenen gerçek sonuçları.",
        "usage": "Geri besleme/değerlendirme."},
    "decision_run_import_sources": {"tr": "Karar–İçe Aktarım Kaynağı", "grup": G_KARAR,
        "desc": "Bir karar çalıştırmasını besleyen import kayıtları.",
        "usage": "İzlenebilirlik (hangi veri hangi karara girdi)."},
    "curriculum_generation_audit": {"tr": "Müfredat Üretim Denetimi", "grup": G_KARAR,
        "desc": "Sonraki yıl müfredat üretiminin denetim kaydı.",
        "usage": "Algoritma Kontrol & Ders Lab."},
    "curriculum_generation_log": {"tr": "Müfredat Üretim Günlüğü", "grup": G_KARAR,
        "desc": "Müfredat üretim adımlarının log kaydı.",
        "usage": "Üretim hattı izleme."},

    # ---- AHP & ağırlık ----
    "ahp_weight_profiles": {"tr": "AHP Ağırlık Profilleri", "grup": G_AHP,
        "desc": "Kriter ağırlıkları, ikili karşılaştırma matrisi ve tutarlılık (CR).",
        "usage": "AHP Ağırlık Yönetimi; karar motoru ağırlıkları."},
    "ahp_profile_approval_logs": {"tr": "AHP Onay Günlükleri", "grup": G_AHP,
        "desc": "AHP profillerinin onay/red akış kayıtları.",
        "usage": "AHP → Onay Akışı."},
    "ahp_profile_policies": {"tr": "AHP Profil Politikaları", "grup": G_AHP,
        "desc": "AHP profillerine bağlı politika ilişkileri.",
        "usage": "Profil-politika eşlemesi."},
    "ahp_sensitivity_results": {"tr": "AHP Duyarlılık Sonuçları", "grup": G_AHP,
        "desc": "Ağırlık değişiminin sonuca etkisi.",
        "usage": "AHP → Etki ve Analiz."},
    "ahp_course_sensitivity_items": {"tr": "AHP Ders Duyarlılığı", "grup": G_AHP,
        "desc": "Ders bazında ağırlık duyarlılık kalemleri.",
        "usage": "Duyarlılık analizi detayı."},

    # ---- Havuz & statü ----
    "havuz": {"tr": "Ders Havuzu", "grup": G_HAVUZ,
        "desc": "Derslerin havuz/müfredat statüsü (1 müfredat, 0 havuz, -1 dinlenme, -2 iptal) ve sayaç.",
        "usage": "Havuz Yönetimi ve yaşam döngüsü."},
    "course_state_transitions": {"tr": "Statü Geçişleri", "grup": G_HAVUZ,
        "desc": "Bir dersin statü değişim geçmişi.",
        "usage": "Havuz Yaşam Döngüsü."},
    "course_state_approvals": {"tr": "Statü Onayları", "grup": G_HAVUZ,
        "desc": "Kritik statü değişikliği onay bekleyenleri.",
        "usage": "Onay Bekleyen Kararlar."},
    "course_state_overrides": {"tr": "Statü İstisnaları", "grup": G_HAVUZ,
        "desc": "Manuel statü override kayıtları.",
        "usage": "Havuz Yönetimi manuel müdahale."},
    "pool_state_policies": {"tr": "Havuz Statü Politikaları", "grup": G_HAVUZ,
        "desc": "Havuz statü geçiş kuralları.",
        "usage": "Yaşam döngüsü state machine."},

    # ---- Dönem planlama ----
    "semester_plan_runs": {"tr": "Dönem Planı Çalıştırmaları", "grup": G_PLAN,
        "desc": "Üretilen Güz/Bahar dönem planlarının başlık kaydı.",
        "usage": "Dönem Planlama → Plan Üret."},
    "semester_plan_course_assignments": {"tr": "Plan Ders Atamaları", "grup": G_PLAN,
        "desc": "Hangi dersin hangi döneme atandığı.",
        "usage": "Güz/Bahar planı tablosu."},
    "semester_plan_constraint_violations": {"tr": "Plan Kısıt İhlalleri", "grup": G_PLAN,
        "desc": "Planın ihlal ettiği kısıtlar (ön koşul, kontenjan vb.).",
        "usage": "Dönem Planlama → Kısıt İhlalleri."},
    "semester_plan_scenarios": {"tr": "Alternatif Plan Senaryoları", "grup": G_PLAN,
        "desc": "Üretilen alternatif dönem planları.",
        "usage": "Dönem Planlama → Alternatif Planlar."},
    "semester_planning_policies": {"tr": "Planlama Politikaları", "grup": G_PLAN,
        "desc": "Hedef ders sayısı, dönem min/max gibi plan kuralları.",
        "usage": "Dönem Planlama politika ayarı."},
    "semester_required_course_loads": {"tr": "Zorunlu Ders Yükleri", "grup": G_PLAN,
        "desc": "Bölümün dönem başına zorunlu ders yükü.",
        "usage": "Plan hedef ayarlamasında."},
    "semester_resource_capacity": {"tr": "Dönem Kaynak Kapasitesi", "grup": G_PLAN,
        "desc": "Sınıf/lab gibi kaynakların dönem kapasitesi.",
        "usage": "Kaynak uygunluğu kontrolü."},
    "course_prerequisites": {"tr": "Ders Ön Koşulları", "grup": G_PLAN,
        "desc": "Derslerin ön koşul ilişkileri.",
        "usage": "Planlamada sıra/ön koşul kontrolü."},
    "course_resource_requirements": {"tr": "Ders Kaynak İhtiyaçları", "grup": G_PLAN,
        "desc": "Dersin lab/sınıf/kaynak gereksinimleri.",
        "usage": "Kaynak uygunluğu ve açılabilirlik."},
    "course_semester_availability": {"tr": "Ders Dönem Uygunluğu", "grup": G_PLAN,
        "desc": "Dersin Güz/Bahar açılabilirlik bilgisi.",
        "usage": "Dönem seçimi ve açılabilirlik skoru."},
    "course_instructor_assignments": {"tr": "Ders Öğretim Üyesi Atamaları", "grup": G_PLAN,
        "desc": "Plan kapsamında ders-hoca atamaları.",
        "usage": "Öğretim üyesi uygunluk/çakışma."},
    "course_time_constraints": {"tr": "Ders Zaman Kısıtları", "grup": G_PLAN,
        "desc": "Ders zaman/çakışma kısıtları.",
        "usage": "Zaman çakışması uyarıları."},
    "instructor_semester_availability": {"tr": "Hoca Dönem Uygunluğu", "grup": G_PLAN,
        "desc": "Öğretim üyesinin dönem bazında uygunluğu.",
        "usage": "Planlamada hoca fizibilitesi."},
    "teaching_resources": {"tr": "Öğretim Kaynakları", "grup": G_PLAN,
        "desc": "Sınıf/lab gibi öğretim kaynaklarının tanımı.",
        "usage": "Kaynak planlaması."},

    # ---- Veri içe aktarım ----
    "criteria_import": {"tr": "Kriter İçe Aktarımları", "grup": G_IMPORT,
        "desc": "Kriter Excel import batch başlıkları.",
        "usage": "Veri Yönetimi → Import geçmişi."},
    "criteria_import_rows": {"tr": "Kriter İçe Aktarım Satırları", "grup": G_IMPORT,
        "desc": "Kriter importunun satır sonuçları.",
        "usage": "Import detayı/satır sonuçları."},
    "survey_import": {"tr": "Anket İçe Aktarımları", "grup": G_IMPORT,
        "desc": "Anket Excel import batch başlıkları.",
        "usage": "Anket Belge Girişi/Veri Yönetimi."},
    "survey_import_rows": {"tr": "Anket İçe Aktarım Satırları", "grup": G_IMPORT,
        "desc": "Anket importunun satır sonuçları.",
        "usage": "Import detayı."},
    "import_batches": {"tr": "İçe Aktarım Toplu İşleri", "grup": G_IMPORT,
        "desc": "Genel import batch kayıtları.",
        "usage": "Veri Yönetimi import geçmişi."},
    "import_diffs": {"tr": "İçe Aktarım Farkları", "grup": G_IMPORT,
        "desc": "Önceki veriyle import farkı başlıkları.",
        "usage": "Diff / Karşılaştırma."},
    "import_diff_items": {"tr": "Fark Kalemleri", "grup": G_IMPORT,
        "desc": "Import farkının satır düzeyi detayları.",
        "usage": "Diff detayı."},
    "import_impact_reports": {"tr": "İçe Aktarım Etki Raporları", "grup": G_IMPORT,
        "desc": "Bir importun kararlara etkisi.",
        "usage": "Karar Etkisi görünümü."},
    "import_quality_checks": {"tr": "İçe Aktarım Kalite Kontrolleri", "grup": G_IMPORT,
        "desc": "Import kalite skoru ve kontrolleri.",
        "usage": "Kalite Kontrol sekmesi."},
    "import_rollback_logs": {"tr": "Geri Alma Günlükleri", "grup": G_IMPORT,
        "desc": "Import geri alma (rollback) kayıtları.",
        "usage": "Rollback & Onay."},
    "import_row_issues": {"tr": "Satır Sorunları", "grup": G_IMPORT,
        "desc": "Import satırlarındaki hatalar.",
        "usage": "Hatalı satır raporu."},
    "secure_import_jobs": {"tr": "Güvenli İçe Aktarım İşleri", "grup": G_IMPORT,
        "desc": "Güvenli import iş başlıkları.",
        "usage": "Güvenli import akışı."},
    "secure_import_job_rows": {"tr": "Güvenli İçe Aktarım Satırları", "grup": G_IMPORT,
        "desc": "Güvenli import satır kayıtları.",
        "usage": "Güvenli import detayı."},

    # ---- ML & benchmark ----
    "ml_algorithm_registry": {"tr": "ML Algoritma Kaydı", "grup": G_ML,
        "desc": "Kayıtlı ML algoritmalarının tanımı.",
        "usage": "Benchmark Lab algoritma kataloğu."},
    "ml_model_runs": {"tr": "ML Model Çalıştırmaları", "grup": G_ML,
        "desc": "ML model eğitim/çalıştırma kayıtları.",
        "usage": "ML Analiz / Benchmark."},
    "ml_predictions": {"tr": "ML Tahminleri", "grup": G_ML,
        "desc": "ML modeli ders tahminleri.",
        "usage": "Destekleyici tahmin (karar bağlayıcı değil)."},
    "ml_prediction_explanations": {"tr": "ML Tahmin Açıklamaları", "grup": G_ML,
        "desc": "SHAP/LIME gibi tahmin açıklamaları.",
        "usage": "ML açıklanabilirlik."},
    "ml_feature_snapshots": {"tr": "ML Öznitelik Görüntüleri", "grup": G_ML,
        "desc": "Modele giren öznitelik anlık kayıtları.",
        "usage": "Tekrarlanabilirlik."},
    "ml_dataset_snapshots": {"tr": "ML Veri Seti Görüntüleri", "grup": G_ML,
        "desc": "Eğitim veri seti anlık kopyaları.",
        "usage": "Veri Seti Laboratuvarı."},
    "ml_readiness_reports": {"tr": "ML Hazırlık Raporları", "grup": G_ML,
        "desc": "ML için veri yeterlilik raporları.",
        "usage": "ML güvenilirlik değerlendirmesi."},
    "algorithm_benchmark_runs": {"tr": "Algoritma Benchmark Çalıştırmaları", "grup": G_ML,
        "desc": "Algoritma karşılaştırma çalıştırmaları.",
        "usage": "Algoritma Karşılaştırma."},
    "algorithm_governance_registry": {"tr": "Algoritma Yönetişim Kaydı", "grup": G_ML,
        "desc": "Algoritmaların kullanım rolü/yönetişimi.",
        "usage": "Algoritma Yönetişimi."},
    "algorithm_task_mapping": {"tr": "Algoritma–Görev Eşlemesi", "grup": G_ML,
        "desc": "Hangi algoritmanın hangi görevde uygun olduğu.",
        "usage": "Algoritma Önerisi."},
    "benchmark_metric_results": {"tr": "Benchmark Metrik Sonuçları", "grup": G_ML,
        "desc": "Benchmark metrik ölçümleri.",
        "usage": "Algoritma karşılaştırma sonuçları."},
    "benchmark_model_diagnostics": {"tr": "Benchmark Model Tanıları", "grup": G_ML,
        "desc": "Model tanı/teşhis çıktıları.",
        "usage": "ML güvenilirlik."},
    "benchmark_statistical_comparisons": {"tr": "İstatistiksel Karşılaştırmalar", "grup": G_ML,
        "desc": "Algoritmalar arası istatistiksel testler.",
        "usage": "Akademik karşılaştırma."},
    "benchmark_validation_results": {"tr": "Benchmark Doğrulama Sonuçları", "grup": G_ML,
        "desc": "Çapraz doğrulama vb. sonuçlar.",
        "usage": "Model doğrulama."},
    "benchmark_data_leakage_reports": {"tr": "Veri Sızıntısı Raporları", "grup": G_ML,
        "desc": "Eğitim/test veri sızıntısı kontrolleri.",
        "usage": "ML güvenilirlik denetimi."},
    "clustering_evaluation_results": {"tr": "Kümeleme Değerlendirmeleri", "grup": G_ML,
        "desc": "Kümeleme algoritması skorları.",
        "usage": "Kümeleme analizi."},

    # ---- Sistem & güvenlik ----
    "alembic_version": {"tr": "Şema Sürümü (Alembic)", "grup": G_SISTEM,
        "desc": "Migration sürüm işareti.",
        "usage": "Şema yönetimi (otomatik)."},
    "schema_compat_logs": {"tr": "Şema Uyumluluk Günlükleri", "grup": G_SISTEM,
        "desc": "Otomatik şema/kolon ekleme kayıtları.",
        "usage": "Migration izleme."},
    "api_clients": {"tr": "API İstemcileri", "grup": G_SISTEM,
        "desc": "API erişim istemci kayıtları.",
        "usage": "API kimlik doğrulama."},
    "security_audit_logs": {"tr": "Güvenlik Denetim Günlükleri", "grup": G_SISTEM,
        "desc": "Güvenlik olayı denetim kayıtları.",
        "usage": "Güvenlik & Hazırlık."},
    "sql_console_audit_logs": {"tr": "SQL Konsol Günlükleri", "grup": G_SISTEM,
        "desc": "SQL konsolunda çalıştırılan sorguların kaydı.",
        "usage": "Denetim/güvenlik."},
    "sqlite_sequence": {"tr": "SQLite Sıra Sayaçları", "grup": G_SISTEM,
        "desc": "AUTOINCREMENT sayaç tablosu (SQLite iç).",
        "usage": "Sistem iç tablosu."},
}


def _fallback(name: str) -> dict[str, str]:
    """Katalogda olmayan tablolar icin makul Turkce baslik/aciklama uret."""
    tr = name.replace("_", " ").strip().title()
    grup = G_SISTEM
    low = name.lower()
    if low.startswith(("benchmark", "ml_", "algorithm", "clustering")):
        grup = G_ML
    elif low.startswith(("import", "secure_import", "criteria_import", "survey_import")):
        grup = G_IMPORT
    elif low.startswith(("semester", "course_prereq", "course_resource", "course_semester", "instructor", "teaching")):
        grup = G_PLAN
    elif low.startswith(("ahp",)):
        grup = G_AHP
    elif low.startswith(("decision", "course_decision", "course_score", "course_trend", "fairness")):
        grup = G_KARAR
    elif low.startswith(("criteria", "data_", "missing")):
        grup = G_KRITER
    return {
        "tr": tr,
        "desc": "Bu tablo için ayrıntılı katalog açıklaması henüz girilmemiş.",
        "usage": "Fiziksel ad: " + name,
        "grup": grup,
    }


def get_table_info(name: str) -> dict[str, str]:
    """Fiziksel tablo adi icin {tr, desc, usage, grup} doner (fallback dahil)."""
    info = TABLE_CATALOG.get(name)
    if info is None:
        return _fallback(name)
    return {"tr": info.get("tr", name), "desc": info.get("desc", ""),
            "usage": info.get("usage", ""), "grup": info.get("grup", G_SISTEM)}


def display_name(name: str) -> str:
    """Listede gosterilecek Turkce ad (fiziksel ad parantez icinde)."""
    return f"{get_table_info(name)['tr']}  ·  {name}"


def physical_from_display(display: str) -> str:
    """Liste etiketinden fiziksel tablo adini geri cozer."""
    if "·" in display:
        return display.rsplit("·", 1)[-1].strip()
    return display.strip()
