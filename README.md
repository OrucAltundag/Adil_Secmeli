# Adil Secmeli - Fakult e Bazli Secmeli Ders Sistemi

Universitelerde secmeli ders secimini veriye dayali ve izlenebilir hale getiren masaustu uygulama + REST API.

## Kurulum

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Konfigurasyon

1. `.env.example` dosyasini `.env` olarak kopyala
2. `DB_PATH` ve `DATABASE_URL` degerlerini ortamina gore guncelle

Opsiyonel: `config.json` ile ayni anahtarlar override edilebilir.

## Migration

```bash
alembic upgrade head
```

## Calistirma

Masaustu:
```bash
python -m app.main
```

Headless / Codespaces:
```bash
python -m app.main --mode api --host 0.0.0.0 --port 8000
```

Not: `python -m app.main` veya `python main.py` komutu GUI olmayan ortamda otomatik olarak API moduna duser.

API:
```bash
uvicorn app.api.main:app --host 0.0.0.0 --port 8000
```

## Kritik Dokumanlar

- [Production Gap Closure](docs/PRODUCTION_GAP_CLOSURE.md)
- [Decision Governance](docs/decision_governance.md)
- [Import Governance](docs/import_governance.md)
- [Criteria Completion Governance](docs/criteria_completion_governance.md)
- [Pool State Machine Governance](docs/pool_state_machine_governance.md)
- [ML Governance](docs/ml_governance.md)
- [Algorithm Governance](docs/algorithm_governance.md)
- [AHP Governance](docs/ahp_governance.md)
- [Semester Planning Governance](docs/semester_planning_governance.md)
- [Architecture](docs/architecture.md)
- [Database Schema Policy](docs/database_schema_policy.md)
- [PostgreSQL Migration Runbook](docs/POSTGRESQL_MIGRATION.md)
- [Developer Guidelines](docs/developer_guidelines.md)
- [Migration Strategy](docs/MIGRATION_STRATEGY.md)
- [Runbook](docs/RUNBOOK_PRODUCTION.md)

Not: Projede cok sayida algoritma bulunmasina ragmen bu algoritmalar ayni karar seviyesinde kullanilmaz. Nihai mufredat/havuz karari AHP + TOPSIS + kural motoru + state machine hattiyla verilir. XGBoost, Naive Bayes, Logistic Regression ve clustering algoritmalari benchmark, baseline veya kesifsel analiz amaciyla kullanilir.

Not: AHP agirliklari kodda sabit tutulmaz; global/fakulte/bolum/yil bazli AHP profillerinden gelir. Her profil ikili karsilastirma matrisi, uretilen agirliklar, consistency ratio, onay durumu ve versiyon bilgisiyle saklanir. Karar calismalari kullanilan AHP profilini ve agirlik snapshot'ini kaydeder.

Not: Donem dengeleme sistemi baslangicta 4+4 varsayilan politikasiyla calisir; ancak bu kural sabit degildir. Fakulte/bolum/yil bazli donem planlama politikalariyla guz ve bahar icin minimum-maksimum ders hedefleri, ders uygunlugu, ogretim uyesi uygunlugu, kaynak kisitlari, on kosullar, kontenjan ve talep dengesi dikkate alinir.

## Test Altyapisi

Test altyapisi yalnizca kodun calisip calismadigini degil; kararlarin matematiksel dogrulugunu, tekrar uretilebilirligini, uc durum dayanikliligini, aciklanabilirligini ve adalet metriklerini de dogrular. Golden dataset ve deterministiklik testleri, ayni veriyle ayni kararin tekrar uretilebilmesini guvence altina alir.

```bash
# Tum testler
python scripts/run_tests.py

# Sadece unit testler
pytest -m unit -v

# Coverage ile
pytest --cov=app --cov-report=html

# Hizli (slow haric)
pytest -m "not slow and not requires_display"
```

Detayli bilgi: [Test Stratejisi](docs/test_strategy.md)

Not: Projede resmi veri erisim yolu SQLAlchemy model + repository/service katmanidir. Alembic resmi schema migration aracidir. Runtime schema compatibility yalnizca eski SQLite dosyalariyla geriye donuk uyumluluk icin kontrollu bir guvenlik agidir. UI ve API dogrudan veritabanina erismez; ortak servisleri kullanir.
