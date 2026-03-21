# Azure Blob Storage Architecture — Stochastic Alpha Engine

## Overview

This document defines the blob storage layout for the Stochastic Alpha Engine. The structure is designed around Hive-style partitioning for efficient predicate pushdown, a dependency-ordered pod computation pipeline, and a `_meta/` layer for provenance and registry tracking.

---

## Container Layout

```
stochastic-alpha-engine/                  ← root container
│
├── pods/
│   ├── raw/
│   │   ├── prices/
│   │   │   └── year=2024/
│   │   │       ├── month=01/
│   │   │       │   └── prices.parquet
│   │   │       └── month=02/
│   │   │           └── prices.parquet
│   │   └── fundamentals/
│   │       └── year=2024/
│   │           └── quarter=Q1/
│   │               └── compustat.parquet
│   │
│   ├── pass1_market/
│   │   └── year=2024/month=01/pass1.parquet
│   ├── pass2_technical/
│   │   └── year=2024/month=01/pass2.parquet
│   ├── pass3_fundamental/
│   │   └── year=2024/month=01/pass3.parquet
│   ├── pass4_risk/
│   │   └── year=2024/month=01/pass4.parquet
│   └── pass5_composite/
│       └── year=2024/month=01/pass5.parquet
│
├── signals/
│   ├── daily/
│   │   └── year=2024/month=01/day=15/signals.parquet
│   └── live/
│       └── 2026-03-18T14:30:00Z.parquet
│
├── models/
│   ├── random_forest/
│   │   ├── v1.2.0/
│   │   │   ├── model.pkl
│   │   │   ├── feature_importance.parquet
│   │   │   └── manifest.json
│   │   └── latest.json                   ← version pointer
│   └── ...
│
├── trades/
│   ├── orders/
│   │   └── year=2024/month=01/orders.parquet
│   └── fills/
│       └── year=2024/month=01/fills.parquet
│
└── _meta/
    ├── pod_registry.json                 ← pod versions + schema validity
    ├── run_log.parquet                   ← pipeline run history
    └── factor_catalog.json              ← 35 factors, groups, dependencies
```

---

## Directory Reference

### `pods/raw/`

Raw ingested data from upstream sources. Partitioned by time. Never overwritten — treat as append-only.

| Path | Source | Cadence |
|---|---|---|
| `raw/prices/year=YYYY/month=MM/` | Alpaca / market data vendor | Daily |
| `raw/fundamentals/year=YYYY/quarter=QN/` | WRDS Compustat + IBES | Quarterly |

---

### `pods/pass{N}_*/`

Precomputed feature store output, organized by the 5 dependency-ordered computation passes. Each pass reads from the previous and writes its own partition.

| Pass | Name | Contents |
|---|---|---|
| 1 | `pass1_market` | Price-derived fields: returns, VWAP, volume ratios |
| 2 | `pass2_technical` | Technical indicators: momentum, RSI, Bollinger, ATR |
| 3 | `pass3_fundamental` | Fundamental factors: earnings yield, book-to-market, accruals |
| 4 | `pass4_risk` | Risk factors: beta, idiosyncratic vol, drawdown |
| 5 | `pass5_composite` | Composite alpha scores, factor z-scores, final feature set |

Each pod file carries Parquet file-level metadata stamped at write time:

```python
{
    b"pod_pass":        b"2",
    b"factor_group":    b"technical",
    b"schema_version":  b"1.2.0",
    b"as_of_date":      b"2026-03-18",
    b"row_count":       b"48210",
    b"universe_filter": b"price>5,adv20>1M",
}
```

---

### `signals/`

Model output written after each scoring run.

- `signals/daily/` — end-of-day batch scores, partitioned by date
- `signals/live/` — intraday scores written with ISO 8601 UTC timestamps as filenames

---

### `models/`

Versioned model artifacts. A `latest.json` pointer file tracks the active version without duplicating large files:

```json
{
  "version": "v1.2.0",
  "path": "models/random_forest/v1.2.0/model.pkl",
  "trained_at": "2026-03-15T09:00:00Z"
}
```

Each version directory contains:
- `model.pkl` — serialized model weights
- `feature_importance.parquet` — per-factor importance scores
- `manifest.json` — training metadata (walk-forward window, universe, hyperparams)

---

### `trades/`

Execution records written by the live trading path. Partitioned by month.

- `orders/` — order submissions sent to Alpaca
- `fills/` — confirmed fill records

---

### `_meta/`

System-level files prefixed with `_` to visually separate them from data paths. These can be assigned a different Azure Blob lifecycle policy (e.g., never expire, replicate to secondary region).

#### `pod_registry.json`

Tracks the validity and schema version of each pod pass. Used by the pipeline to determine whether a recompute is needed.

```json
{
  "pass1_market": {
    "schema_version": "1.2.0",
    "last_run": "2026-03-18T08:00:00Z",
    "row_count": 48210,
    "status": "valid"
  },
  "pass2_technical": {
    "schema_version": "1.2.0",
    "last_run": "2026-03-18T08:05:00Z",
    "row_count": 48210,
    "status": "valid"
  }
}
```

#### `run_log.parquet`

Append-only log of every pipeline execution. Columns: `run_id`, `pass`, `started_at`, `finished_at`, `status`, `row_count`, `error`.

#### `factor_catalog.json`

Canonical registry of all 35 retained alpha factors — groups, equations, pod column dependencies, and data sources. Should match `FACTORS_REFERENCE.md`.

---

## Partitioning Strategy

All time-series data uses **Hive-style partitioning** (`year=YYYY/month=MM/`). This allows Polars and PyArrow to prune partitions at scan time without loading the full dataset:

```python
# Polars — only scans the partitions matching the filter
df = (
    pl.scan_parquet("az://stochastic-alpha-engine/pods/pass2_technical/**/*.parquet")
    .filter(pl.col("year") == 2024, pl.col("month") == 1)
    .collect()
)
```

---

## Conventions

- **Never put dates in filenames.** Use the directory path for partitioning (`year=2024/month=01/`), not `signals_2024_01_15.parquet`. Filename-based dates break partition pruning.
- **Never mix raw and derived data** under the same prefix. Separate lifecycle policies apply to `raw/` vs `pass{N}/`.
- **Avoid single large parquet dumps.** Partition so partial reads are possible.
- **`_meta/` prefix** signals system/registry files and can carry a separate Azure lifecycle policy.
- **No symlinks in blob storage.** Use `latest.json` pointer files for mutable "current version" references.
- **Parquet metadata** travels with the file to Azure Blob and can be inspected without loading the data payload via `pq.read_schema()`.

---

## Reading Parquet Metadata Without Loading Data

```python
import pyarrow.parquet as pq

schema = pq.read_schema("pods/pass2_technical/year=2024/month=01/pass2.parquet")
meta = schema.metadata

print(meta[b"schema_version"])  # b"1.2.0"
print(meta[b"as_of_date"])      # b"2026-03-18"
```

---

## Azure Blob Lifecycle Policy Recommendations

| Prefix | Retention | Notes |
|---|---|---|
| `pods/raw/` | Indefinite | Source of truth, never expire |
| `pods/pass{N}_*/` | 90 days rolling | Recomputable from raw |
| `signals/daily/` | 1 year | Needed for backtest attribution |
| `signals/live/` | 30 days | Short-lived intraday artifacts |
| `models/` | Indefinite | All versions retained for reproducibility |
| `trades/` | Indefinite | Regulatory / audit trail |
| `_meta/` | Indefinite | Replicate to secondary region if possible |
