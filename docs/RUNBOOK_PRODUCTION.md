# Runbook (Deploy / Rollback / Backup)

## 1. Deploy

1. Kodu al:
   - `git pull`
2. Sanal ortam + bagimlilik:
   - `pip install -r requirements.txt`
3. Ortam degiskeni:
   - `.env.example` dosyasini `.env` olarak kopyala ve `DB_PATH`/`DATABASE_URL` ayarla
4. Migration:
   - `alembic upgrade head`
5. Smoke check:
   - API: `uvicorn app.api.main:app --host 0.0.0.0 --port 8000`
   - `/api/v1/akademik-plan?fakulte_id=1&yil=2025` cevabinda `overlap_count=0` kontrol et

## 2. Backup

1. Uygulamayi bakim moduna al (yazma isteklerini durdur).
2. Dosya yedegi:
   - `copy data\\adil_secmeli.db data\\backup\\adil_secmeli_YYYYMMDD_HHMM.db`
3. Yedek dogrulama:
   - Kopya dosyada tablo sayisi ve row count check.

## 3. Rollback

1. Uygulama stop.
2. Migration rollback:
   - `alembic downgrade -1`
   - Not: SQLite veri-kaybi riskini azaltmak icin downgrade bu revizyonda index rollback yapar.
3. DB restore gerekiyorsa:
   - `copy data\\backup\\adil_secmeli_YYYYMMDD_HHMM.db data\\adil_secmeli.db /Y`
4. Uygulamayi yeniden baslat.

## 4. Incident Checklist

- `havuz` tablosunda `donem` kolonu var mi?
- `uq_havuz_ders_fac_yil_donem` index aktif mi?
- `api/v1/havuz?yil=...&fakulte_id=...&donem=...` cevap veriyor mu?
- `api/v1/akademik-plan` overlap_count > 0 ise dual-semester rebalance tekrar calistir:
  - `rebuild_school_curricula_dual_semester(...)`

