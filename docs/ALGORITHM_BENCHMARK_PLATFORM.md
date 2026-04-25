# Algorithm Benchmarking and Decision Support Platform

This document describes the production-grade extension that converts Adil Secmeli from a single-purpose course tool into a modular algorithm benchmarking framework.

## Architecture

The implementation follows the report's layered structure:

- `app/datasets/`
  - real loaders (`loaders.py`)
  - feature engineering (`feature_engineering.py`)
  - synthetic generator with bootstrap/noise/imbalance/capacity scaling (`synthetic_generator.py`)
  - pipeline orchestration (`preprocess.py`)
  - core entities (`entities.py`)
- `app/algorithms/`
  - base contracts (`base.py`)
  - MCDM (`mcdm/ahp.py`, `topsis.py`, `vikor.py`, `promethee.py`)
  - ML baselines/core/advanced fallback (`ml/baselines.py`, `ml/classifiers.py`)
  - clustering (`clustering/models.py`)
  - allocation/optimization (`allocation/allocators.py`)
- `app/benchmark/`
  - algorithm registry (`registry.py`)
  - scenario templates (`scenarios.py`)
  - experiment runner (`runner.py`)
  - result persistence (`result_store.py`)
- `app/metrics/`
  - classification, ranking, clustering, fairness, performance, academic consistency
- `app/services/`
  - decision engine (`algorithm_manager.py`)
  - orchestration facade (`experiment_service.py`)
- `app/dashboard/`
  - benchmark REST routes (`api_routes.py`)
  - response serializers (`serializers.py`)

## Implemented Entity Set

Canonical entities are defined in `app/datasets/entities.py`:

- `Student`
- `Course`
- `Preference`
- `SurveyResponse`
- `Allocation`
- `BenchmarkRun`
- `MetricResult`

## Data Layers

The pipeline enforces separation of:

- `raw_real`
- `derived`
- `synthetic`

Derived features include:

- one-hot encoding
- min-max normalization (0-1)
- composite scores (`academic_preparedness`, `preference_strength`, `satisfaction_signal`, `course_capacity_signal`, `composite_score`)

Synthetic generation supports:

- bootstrap sampling
- numeric noise injection
- class imbalance controls
- capacity constraints
- scale tiers: `5k`, `10k`, `50k`, `100k`, `250k`

## Algorithm Interface Contract

All algorithms follow `IAlgorithm` and return standardized `AlgorithmOutput` containing:

- predictions/recommendations/assignments
- confidence
- explanation
- runtime
- parameters

Sub-interfaces:

- `IPredictor`
- `IRanker`
- `IAllocator`
- `IClusterer`

## API Endpoints (Benchmark)

Mounted under `/api/v1/benchmark`:

- `GET /scenarios`
- `GET /algorithms?group=...`
- `POST /datasets/load`
- `POST /runs/execute`
- `POST /runs/compare`
- `POST /recommendation`
- `GET /runs`
- `GET /runs/{run_id}`

## Example Assets

- Example dataset: `data/benchmark/raw_real/*.csv`
- Example run payload: `reports/benchmark_runs/example_run_payload.json`
- Repro script: `app/scripts/run_benchmark_example.py`

