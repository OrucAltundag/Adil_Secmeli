# UI Pylance Hataları — 2026-06-10

UI sayfaları açılıp kontrol edildiğinde Pylance'in tespit ettiği aktif tip
hatalarının listesi. Düzeltme planı en altta.

## Dosya: `app/ui/benchmark/pages/comparison_page.py`

Pylance kuralı: `reportArgumentType`

`dict.get(...)` çağrılarının dönüş tipi `Unknown | None`. Doğrudan `float(...)`
fonksiyonuna verildiğinde Pylance `None` ihtimalinden dolayı uyarı üretiyor.
Mevcut kodda `try/except (TypeError, ValueError)` zaten var; runtime'da sorun
yok ama statik analiz `None` durumunu görmüyor.

| # | Satır | İfade | Bağlam |
|---|-------|-------|--------|
| 1 | 264 | `metric_value = float(out.get(metric))` | `_with_baseline_fields` |
| 2 | 284 | `return float(row.get(metric))` | `_baseline_value` |
| 3 | 300 | `val = float(row.get(metric))` | `_compute_significance_map` |
| 4 | 335 | `val = float(row.get(metric))` | `_compute_ci_map` |

## Düzeltme Yaklaşımı

Aynı şablon dört kez tekrarlandığı için tek bir yardımcı fonksiyon eklemek
en verimli yol:

```python
def _safe_float(value: object) -> float | None:
    """`None` veya dönüştürülemez değerleri sessizce `None`'a indirger."""
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
```

Sonra 4 çağrı şu şekilde yeniden yazılacak:

- Satır 264: `metric_value = _safe_float(out.get(metric))` — try/except artık
  gerekli değil.
- Satır 284: doğrudan `return _safe_float(row.get(metric))`.
- Satır 300 / 335: `val = _safe_float(row.get(metric)); if val is None: continue`.

Davranış birebir korunur (None → atla / None → boş baseline), kullanıcının
"incremental & non-breaking" tercihine uygundur.

---

## Pyright Tam Tarama (app/ui) — 39 Hata

`comparison_page.py` düzeltildikten sonra projedeki UI alt klasöründe kalan
hataları `pyright` ile listeledim.

### `app/ui/benchmark/api_client.py`
- **L67** — `mock_data.get_mock_recommendation(body)` çağrısı dict gönderiyor,
  ama imza `problem_type: str`. Mock fonksiyon zaten runtime'da
  `isinstance(problem_type, dict)` ile dallanıyor → imzayı `str | dict[...]`
  yap.

### `app/ui/benchmark/benchmark_panel.py`
- **L158/160** — `page = pages.get(...)` Optional[Frame]; `hasattr` ile
  korunsa da pyright daraltma yapmıyor. `getattr(page, name, None)` ile
  callable alıp çağıracağız.

### `app/ui/benchmark/pages/dashboard_page.py`
- **L307-323** — `summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}` deseni narrow olmuyor (iki ayrı çağrı).
  Önce ham değişkene atayıp ardından isinstance kontrolüyle yeniden bağla.

### `app/ui/benchmark/pages/run_history_page.py`
- **L324-326** — Aynı pattern (`details = detail.get("details") if isinstance(...)`).

### `app/ui/benchmark/widgets.py`
- **L40** — `if on_error: ... lambda exc=exc: on_error(exc)`; lambda
  içinde narrow kaybediliyor. Lambda dışında non-optional bind yap.

### `app/ui/tabs/analysis_tab.py`
- **L214/260** — `sns` ismi tanımsız. `import seaborn as sns` modül
  başına eklenecek (matplotlib pasta/barplot için).

### `app/ui/tabs/calc_tab.py`
- **L956/962/969/970/975** — Pandas DataFrame typing: `show.columns = [...]`
  atama sonrası pyright DataFrame tipini Series/ndarray olarak görüyor.
  `rename(columns=...)` ile değiştir.

### `app/ui/tabs/course_analysis_tab.py`
- **L873/1078** — `criteria_status: dict = None` ve `steps: dict = None`
  imzaları. `dict | None = None` yap.
- **L1096** — `_STATU_LABELS.get(statu, label)` sonucu `str | None`
  görülüyor; çevre `text=` parametresi `float | str` istiyor. `or ""`
  veya `str(...)` ile zorla.

### `app/ui/tabs/decision_center_page.py`
- **L232** — `tk.W` Literal'a daralmıyor. `tk.W` yerine doğrudan
  `"w"` literal kullan (tk.W zaten `"w"`).

### `app/ui/tabs/semester_planning_page.py`
- **L613** — `int(row.get("id"))` None gelebilir. `safe_int` yardımı yok;
  inline guard ekle (`raw = row.get("id"); int(raw) if raw is not None else 0`).

### `app/ui/tabs/tools_tab.py`
- **L676/805/862** — `db_path=self.db_path` Optional görünüyor. Aynı sınıfta
  tutarlı şekilde `db_path` zorunlu str alıyor mu kontrol et; gerekirse
  çağrı öncesi guard ekle.

---

## Proje Geneli Tarama Özeti — 2026-06-11

İkinci tur taramada `pyright` ile tüm `app/` ağacı kontrol edildi.

### Baseline'lar

| Aşama | Hata Sayısı |
|------|-------------|
| Başlangıç (UI hariç) | 642 |
| `pandas-stubs` kurulumundan sonra | 283 |
| Üretim kodu temizliği bittiğinde | **152** (yalnız `tests/`) |
| Üretim kodu (her klasör) | **0** |

### Üretim kodunda yapılan başlıca düzeltmeler

- **app/services** (132 → 0): `xls.parse()` çağrıları `pd.read_excel(xls, ...)`'a alındı (stub uyumu); sklearn `zero_division` parametresi için `_zd: Any = 0` deseni; `ml_analysis_service` `exp_err` olası bağlanmamışlık; `ml_prediction_service` `model.predict()` döngülerine `Any` annotasyon; `reporting_service` `ders_id` None kontrolü; `validation_strategy_service` `estimator: Any`.
- **app/algorithms** (113 → 0): allocator'larda `assigned: dict[int, int | None]` annotasyonu; `.fillna()` zincirini Series'e dönüştürme; AHP'de `np.real(eigenvalues)`, `pd.DataFrame` annotasyonu, item_id güvenli erişim.
- **app/api** (11 → 0): `tuple(params) + (limit,)`; `payload.year` None guard'ı; `recommended_status` int dönüşümü; `int = None` defaultları `int | None = None`; `Field(default=None, ...)`.
- **app/db** (9 → 0): `_engine_ready()` yardımcısı (assert ile Optional darlığı); `SessionLocal()` None kontrolü; `Engine` import'u.
- **app/etl + scripts + datasets + benchmark + metrics + health + dashboard + utils** — Optional varsayılanlar, `_col()` helper'ları, `require_database()` accessor'ı, file-level pyright direktifi (yalnız `utils/import_excel.py` için legacy ORM stub gürültüsü).

### Bağımlılık ekleme

- `pandas-stubs` paketi geliştirme bağımlılığı olarak kuruldu. (`requirements.txt`'e
  henüz yansıtılmadı; gerekirse `requirements-dev.txt`/`pyproject.toml`'a eklenebilir.)

### Kalan kapsam — `app/tests/` (152 hata)

Test dosyalarındaki hatalar üretim koduyla doğrudan ilgili değil; iki ana
kalıp:
1. **Eski şema isimleri** — `test_pydantic_schemas.py` (50), `test_api_validation_schemas.py` (29) gibi dosyalar `year=`, `faculty_id=` gibi eski parametre isimleri kullanıyor; yeni şemada `yil=`, `fakulte_id=` olarak yeniden adlandırılmış. Bu testlerin runtime'da hâlâ geçip geçmediği ayrı bir incelemeyi gerektirir.
2. **Test stub'ları** — `test_criteria_page.py` `_DummyEntry`/`_DummyLabel` ile `tkinter.Entry`/`Label` alanlarını maskeliyor. Runtime test mantığı için olağan kalıp; pyright maskeleme için `cast` veya `# type: ignore` kullanılabilir.

Bu testler ayrı bir iş paketinde ele alınmalı; üretim kodu davranışını
etkilemiyor.


