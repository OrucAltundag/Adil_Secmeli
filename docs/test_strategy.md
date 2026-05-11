# Test Stratejisi — Adil Seçmeli Karar Destek Sistemi

## Genel Bakış

Test altyapısı yalnızca kodun çalışıp çalışmadığını değil; kararların matematiksel doğruluğunu, tekrar üretilebilirliğini, uç durum dayanıklılığını, açıklanabilirliğini ve adalet metriklerini de doğrular. Golden dataset ve deterministiklik testleri, aynı veriyle aynı kararın tekrar üretilebilmesini güvence altına alır.

## Test Kategorileri

| Kategori | Marker | Açıklama |
|----------|--------|----------|
| Unit | `unit` | İzole birim testleri — AHP, TOPSIS, trend, confidence |
| Integration | `integration` | Servisler arası akış testleri |
| E2E | `e2e` | Uç-uca karar pipeline testleri |
| Regression | `regression` | Golden dataset ve deterministiklik |
| API | `api` | FastAPI endpoint smoke testleri |
| UI | `ui` | Modül import ve widget smoke testleri |
| DB | `db` | Schema compatibility ve migration |
| Benchmark | `benchmark` | ML minimum sample guard ve governance |
| Performance | `performance` | Büyük veri zamanlama testleri |

## Test Nasıl Çalıştırılır

```bash
# Tüm testler
python scripts/run_tests.py

# Sadece unit testler
python scripts/run_tests.py --unit

# Coverage ile
python scripts/run_tests.py --coverage

# Hızlı (slow hariç)
python scripts/run_tests.py --quick

# pytest doğrudan
pytest -m unit -v
pytest -m "not slow" --cov=app --cov-report=html
```

## Golden Dataset

`app/tests/fixtures/test_db_builders.py` içinde 8 ders ile kontrollü senaryo seti:
- Yüksek skorlu ders (müfredatta kalmalı)
- Düşük skorlu ders (havuza düşmeli)
- Çok düşük skorlu ders (iptal adayı)
- Stratejik/korumalı ders
- Eksik verili ders (düşük güvenli)
- Eşit skorlu dersler (tie-break senaryosu)
- Yeni ders (grace period)

## AHP Matematiksel Testler

- Birim matris → eşit ağırlıklar
- Bilinen 3x3 ve 4x4 matrisler → beklenen ağırlıklar (toleranslı)
- Ağırlık toplamı = 1.0
- Tutarlı matris CR ≤ 0.10
- Tutarsız matris CR > 0.10
- n=1 ve n=2 güvenli çalışma

## TOPSIS Matematiksel Testler

- Closeness coefficient 0-1 aralığında
- Bilinen sıralamayla doğrulama
- Tüm değerler aynıyken NaN/ZeroDivision kontrolü
- Tek alternatif çalışma
- Eksik değer (NaN) güvenli işleme

## State Machine Transition Matrix

11 senaryo test edilir (bkz. `test_state_machine.py`):
1. Müfredatta + düşük skor → havuz/dinlenme
2. Havuzda + uzun süre düşük → dinlenme
3. Dinlenmede + çok düşük + yüksek güven → cancel_candidate
4. Düşük güven → cancel engellenir
5. Stratejik ders koruması
6. Akreditasyon koruması
7. Yeni ders grace period
8. Revize ders grace period
9. Yüksek skor + rising → reactivation
10. Kalıcı iptal → otomatik dönüş yok
11. Manuel override

## Deterministiklik

Aynı veri + aynı ayarlar + aynı seed = aynı karar. 5 ardışık çalışma karşılaştırılır.

## Coverage Hedefleri

- Genel: %60+
- Algoritmalar: %90+
- Kritik servisler: %80+
