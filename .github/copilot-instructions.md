# Copilot Instructions for Adil Seçmeli

## Project Overview
**Adil Seçmeli** is a fairness-based elective course recommendation and assignment system for universities. It scores courses using three components (performance, popularity, survey feedback) and automatically assigns electives to students while maintaining transparency and fairness. The system uses a hybrid model: 2 auto-assigned courses + 2 student-chosen courses per semester.

---

## Architecture Fundamentals

### Core Data Flow
1. **Input Data**: Course metadata (bilgi/description), student performance scores, enrollment data
2. **Scoring**: `KararMotoru` (AHP+TOPSIS) computes weighted course scores → `AHP_TOPSIS_Skor`
3. **Assignment**: Matching algorithm assigns top-scoring courses to students respecting quotas
4. **Output**: Transparent assignment records with decision rationale

### Key Service Layers
- **Calculation Engine** (`app/services/calculation.py`): AHP (Analytic Hierarchy Process) + TOPSIS ranking; `KararMotoru.ahp_calistir()` returns hardcoded 4-criterion weights
- **Similarity Engine** (`app/services/similarity_engine.py`): TF-IDF vectorization of course descriptions; used for course similarity matching (ngram_range=(1,2) critical for academic Turkish text)
- **Database Layer** (`app/db/`): SQLite ORM via SQLAlchemy; models enforce relationships (Okul→Fakülte→Bolum→Ogrenci→Kayıt)
- **State Management** (`app/core/state.py`): Centralized app state with event listener pattern (`.on()` / `.set()`)
- **UI Framework** (`app/ui/tabs/`): Tkinter with ttk widgets; PoolTab, AnalysisTab, CalcTab pattern

### Configuration Pattern
- `config.json` overrides defaults from `app/core/config.py`
- Database path: resolved dynamically from `config.json` → absolute path handling critical for portability
- Logger singleton in `app/utils/logger.py`: use for all debug/audit trails

---

## Critical Developer Workflows

### Database Initialization
```bash
# Run scripts in order:
python app/scripts/init_script.py        # Schema creation
python app/scripts/smart_data_generator.py  # Test data
python app/scripts/havuz_kumulatif_doldur.py  # Pool population
```

### Running the UI Application
```bash
cd Adil_Secmeli_Python
python app/main.py  # Launches Tkinter GUI
```

### Running Tests
```bash
pytest app/tests/test_score_engine.py     # Scoring logic
pytest app/tests/test_similarity.py       # NLP vectorization
pytest app/tests/test_assignment_engine.py # Auto-assignment
```

### Common ETL Operations
- **Import course catalog**: `app/etl/import_mufredat_excel.py` (cleans 2022 data without touching pool)
- **Sync student enrollments**: `app/scripts/import_real_data.py`
- **Repopulate pool**: `app/scripts/update_db_for_pool.py`

---

## Project-Specific Patterns & Conventions

### 1. SQL Escaping Pattern
All user input into SQL queries must use `_sq(s)` helper:
```python
def _sq(s: str) -> str:
    return str(s).replace("'", "''")
```
Example: `f"SELECT * FROM ders WHERE ad = '{_sq(course_name)}'"`

### 2. Turkish Language Handling
- Column/table names are Turkish: `ders`, `ogrenci`, `bilgi`, `bolum`
- NLP (`similarity_engine.py`) uses `stop_words=None` (TR stopwords not auto-included)
- Use UTF-8 encoding explicitly: `open(file, encoding="utf-8")`

### 3. Weight & Configuration Versioning
- Scoring weights (wB, wP, wA) live in `config.json`, not hardcoded
- AHP weights currently hardcoded in `KararMotoru.ahp_calistir()` — should be externalized if rules change
- Every config change should be logged via audit trail

### 4. Database Connection Pattern
```python
# Use app/db/sqlite_db.py Database class for connections
db = Database()
conn = db.get_connection()  # Manages close automatically
```
**Never** use raw `sqlite3.connect()` in new code — use the wrapper for centralized path resolution.

### 5. UI State Binding Pattern
State changes trigger callbacks:
```python
self.app.state.on("selected_faculty", lambda v: self.refresh_courses(v))
self.app.state.set("selected_faculty", new_value)  # Fires listener
```

### 6. DataFrame Normalization
Scoring normalizes columns via:
```python
paydalar = {c: math.sqrt(sum((float(x) ** 2) for x in df[c].fillna(0))) or 1 for c in sutunlar}
```
Always fill NaN before norm calculations to prevent silent zero-division.

---

## Integration Points & Dependencies

### External Libraries (Key Usage)
| Library | Purpose | Critical Details |
|---------|---------|-----------------|
| pandas | Data manipulation | Load SQL queries into DataFrames; normalize before scoring |
| scikit-learn | Similarity vectorization | TF-IDF with `max_features=5000, ngram_range=(1,2)` |
| SQLAlchemy | ORM | Declarative Base models; relationships auto-load |
| Tkinter | UI rendering | Backend `matplotlib.use("TkAgg")` required for charts |

### Cross-Component Dependencies
- **Calculation** needs course metadata from **Database** (`ders` table)
- **Similarity Engine** reads only from `ders` table; does NOT modify state
- **Assignment** depends on course scores + student enrollments + quotas
- **UI** queries state; never queries DB directly (route through services)

---

## Common Gotchas & Solutions

| Issue | Root Cause | Solution |
|-------|-----------|----------|
| "Ders ID bulunamadı" in NLP | Course has no `bilgi` text | Filter for `WHERE LENGTH(bilgi) > 1` before vectorization |
| Import fails silently | Excel encoding mismatch | Force `encoding="utf-8"` + verify column names are lowercase |
| State listener not firing | Callback exception swallowed | Check exception handler in `app/core/state.py:set()` |
| Scoring returns NaN | Division by zero in normalization | Ensure `or 1` fallback in paydalar calculation |
| Database locked | Concurrent connection without close | Always close cursor/connection: use context managers or wrapper class |

---

## Code Structure Quick Reference

- **Entry**: [app/main.py](app/main.py) — Tkinter app initialization, tab construction
- **Scoring Logic**: [app/services/calculation.py](app/services/calculation.py) — `KararMotoru` class
- **Models**: [app/db/models.py](app/db/models.py) — SQLAlchemy ORM definitions
- **Config**: [app/core/config.py](app/core/config.py) + [config.json](config.json)
- **Tests**: [app/tests/](app/tests/) — pytest fixtures + data validation
- **Scripts**: [app/scripts/](app/scripts/) — One-off utilities (no imports between them)

---

## When Adding New Features

1. **New scoring algorithm?** Extend `KкараMotoru`; externalize weights to `config.json`
2. **New database entity?** Add SQLAlchemy model to [app/db/models.py](app/db/models.py); write migration script
3. **New UI section?** Create tab class in [app/ui/tabs/](app/ui/tabs/); wire state listeners
4. **New ETL pipeline?** Place in [app/scripts/](app/scripts/); document input/output in README
5. **Performance issue?** Profile with small data first; cache expensive DB queries in `AppState.results_cache`

---

## Notes for AI Assistants
- This is a **Turkish university system** context; adapt examples to Turkish terminology
- Fairness & transparency are core design principles; maintain audit trails for all decisions
- DB schema versioning is minimal; review [data/schema.sql](data/schema.sql) before migrations
- Config-driven approach enables rule changes without code redeployment
