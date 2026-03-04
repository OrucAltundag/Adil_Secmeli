# Adil Seçmeli — Fakülte Bazlı Seçmeli Ders Öneri ve Atama Sistemi

Üniversitelerde seçmeli ders seçimini veriye dayalı ve adil hale getiren masaüstü uygulaması ve REST API.

---

## Kurulum

```bash
# 1. Sanal ortam (önerilir)
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/macOS

# 2. Bağımlılıkları yükle
pip install -r requirements.txt

# 3. Veritabanı başlatma (ilk kurulum)
python -m app.scripts.init_script
python -m app.scripts.smart_data_generator
python -m app.scripts.havuz_kumulatif_doldur
```

---

## Çalıştırma

**Masaüstü uygulaması:**
```bash
python -m app.main
```

**REST API (Üniversite entegrasyonu):**
```bash
python -m uvicorn app.api.main:app --reload --host 0.0.0.0
```
API dokümantasyonu: http://localhost:8000/docs

---

## Proje Yapısı

| Klasör | Açıklama |
|--------|----------|
| `app/main.py` | Ana uygulama girişi |
| `app/ui/tabs/` | Sekmeler (Tablo, Analiz, Rapor, Hesaplama) |
| `app/services/` | Hesaplama, havuz kararı, benzerlik |
| `app/db/` | Veritabanı (SQLite, SQLAlchemy) |
| `app/api/` | REST API (dersler, skorlar, havuz, müfredat) |
| `docs/` | Modül haritası, entegrasyon planı |

Detaylı modül haritası: [docs/MODUL_HARITASI.md](docs/MODUL_HARITASI.md)

---

## Dokümantasyon

- [Modül Haritası](docs/MODUL_HARITASI.md) — Hangi .py dosyası ne işe yarar
- [Üniversite Entegrasyon Planı](docs/UNIVERSITE_ENTEGRASYON_PLANI.md) — Adım adım entegrasyon
- [Proje Analiz Raporu](docs/PROJE_ANALIZ_RAPORU.md) — Eksiklikler ve öneriler
- [Yeniden Yapılandırma Planı](docs/PROJE_YENIDEN_YAPILANDIRMA_PLANI.md) — Veri mimarisi
