# Production Gap Closure (P0/P1)

## 1. GAP -> ROOT CAUSE -> FIX Matris

| Alan | Gap | Root Cause | Risk | Fix | Oncelik |
|------|-----|------------|------|-----|---------|
| Veri modeli | `havuz` tablosunda donem ekseni yok | Yil tek boyutlu tutulmus | Guz/Bahar cakismasi, duplicate status | `havuz.donem` + composite unique + runtime migration guard | P0 |
| Migration | Surumlu migration disiplini yok | `ALTER` scriptleri dağınık | Prod drift / rollback zorlugu | Alembic (`alembic/env.py`, ilk revision) + runtime backward compat | P0 |
| Mufredat uretimi | Dual-semester pipeline yok | Tek donemli rebuild | 8 dersin 4+4 dagitimi garanti degil | `rebuild_school_curricula_dual_semester()` + rebalance motoru | P0 |
| State machine | Donem-aware degil | Status sadece yil bazli | Cross-semester uyumsuz statu/sayac | `calculate_next_status_semester()` + conflict guard | P0 |
| Raporlama | Skor kaynagi daginik | UI ve servislerde coklu skor akisi | Tutarsiz rapor | `reporting_service.py` + tek kaynak `skor` tablosu | P0 |
| Test | Semester coverage eksik | Sadece tek donem testleri | Regression riski | `test_semester_support.py` (unit+integration) | P0 |
| Operasyon | `.env` standardi / runbook yok | Config ve deploy adimlari dağınık | Hata durumunda yavas recovery | `app/core/settings.py`, `.env.example`, runbook adimlari | P0 |
| API/UX | `donem` param standard degil | Endpointler farkli davranıyor | Integrasyon karmaşası | API donem normalize + `akademik-plan` endpoint | P1 |

## 2. P0 Uygulama (Kritik Kapanis)

### 2.1 Veri Modeli (Donem Kirilimi)
- ORM: `app/db/models.py` -> `Havuz.donem` eklendi.
- Composite unique: `uq_havuz_ders_fac_yil_donem`.
- Backward compatibility:
  - `app/db/schema_compat.py::ensure_havuz_semester_schema`
  - Legacy DB acilisinda kolon + index + normalize + dedupe.

### 2.2 Migration Disiplini
- Alembic setup:
  - `alembic.ini`
  - `alembic/env.py`
  - `alembic/versions/20260324_0001_havuz_semester_axis.py`
- Source of truth:
  - Runtime: SQLAlchemy models + Alembic revision
  - Operational guard: `ensure_havuz_semester_schema` (saha uyumlulugu)
- Normalizasyon:
  - Legacy `donem` bos/bozuk -> `Guz/Bahar`
  - Duplicate havuz satirlari -> composite key ile tekilleme

### 2.3 Dual Semester Engine
- Tam kod: `app/services/dual_semester.py`
- Giris noktasi: `app/services/calculation.py::rebuild_school_curricula_dual_semester`
- Algoritma:
  1. Future curricula reset
  2. Guz + Bahar stable generation
  3. Department bazli 4+4 rebalance
  4. Cross-semester duplicate temizligi
  5. Donem-aware havuz state sync

### 2.4 State Machine Refactor
- Legacy bozulmadan korunur: `calculate_next_status`
- Yeni donem-aware fonksiyonlar:
  - `calculate_next_status_semester`
  - `enforce_cross_semester_constraints`
- Dosya: `app/services/havuz_karar.py`

## 3. P0 - Raporlama & Skor Motoru Merkezi

- Yeni merkez servis: `app/services/reporting_service.py`
- Tek skor kaynagi: `skor` tablosu (`ensure_score_source_schema`)
- UI bagimsiz snapshot:
  - `ensure_report_scores`
  - `build_report_snapshot`
- Geriye uyum:
  - `app/services/reporting.py` facade olarak yeni servise delege eder.

## 4. P0 - Test Stratejisi

- Unit:
  - Cross-semester conflict guard
  - State machine donem gecisi
- Integration:
  - Dual-semester rebuild (4+4 + no overlap)
  - Schema backward compatibility migration
- Dosya:
  - `app/tests/test_semester_support.py`

## 5. P0 - Operasyonel Urunlesme

- `.env` standardi:
  - `.env.example`
  - `DB_PATH`, `DATABASE_URL`, `API_HOST`, `API_PORT`, `LOG_LEVEL`
- Config management:
  - `app/core/settings.py` (env + `config.json` fallback)
  - `app/db/database.py` ve `app/api/routes.py` bu kaynagi kullanir.
- Migration rollback:
  - Alembic downgrade sadece indexleri geri alir (SQLite data-loss riskini azaltir).

## 6. P1 - UX & API Tamamlama

- API donem standardi:
  - `/havuz`, `/mufredat`, `/skorlar` donem normalize eder.
- Akademik plan endpoint:
  - `/api/v1/akademik-plan?fakulte_id=&yil=`
  - Guz/Bahar ders listesi + overlap + 4+4 denge flag'i.
- 4+4 blok goruntuleme mantigi:
  - Endpoint cevabinda `balanced_4_plus_4`, `overlap_count`.

## 7. Karar Gerektiren Noktalar

1. Migration stratejisi:
   - A: Sadece Alembic
   - B: Sadece runtime ALTER
   - C: Alembic + runtime guard
   - Final: C (deploy disiplini + saha uyumlulugu birlikte)
2. Skor kaynagi:
   - A: `havuz.skor`
   - B: `skor` tablosu
   - C: ikili kaynak
   - Final: B (rapor tek kaynaktan), `havuz.skor` sadece UI backward compat.
3. Dual-semester enforcement:
   - A: Tek pass brute force
   - B: Guz/Bahar ayri, sonra rebalance
   - C: Tam yeni optimizer
   - Final: B (mevcut pipeline ile en dusuk regresyon riski)

## 8. Final Checklist (Go-Live)

- [x] Migration guvenli
- [x] Guz sistemi bozulmadi (legacy state machine korunuyor)
- [x] Bahar aktif (dual-semester rebuild var)
- [x] Cross-semester garanti (constraint enforcement)
- [x] Test coverage (semester support testleri eklendi)
- [x] Rollback hazir (alembic downgrade stratejisi tanimli)

