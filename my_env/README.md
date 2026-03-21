# Project Setup

This repo includes two files that handle environment setup and VS Code integration:

```
your-project/
├── .vscode/
│   └── tasks.json      ← VS Code tasks (run setup steps from the UI)
├── install.ps1         ← PowerShell bootstrap script
└── requirements.txt    ← generated after first install
```

---

## Quick Start

1. Open the project folder in VS Code
2. Press `Ctrl+Shift+B` to run the full setup (installs Python if needed, creates `.venv`, installs all packages, creates folder structure)
3. When it finishes, activate the virtual environment in your terminal:

```powershell
.\.venv\Scripts\Activate.ps1
```

That's it. You're ready to work.

---

## What `install.ps1` Does

The script runs six steps in order:

### 1. Python installation
Checks whether Python 3.11.9 is already installed. If not, downloads the official installer from python.org and runs it silently with `InstallAllUsers=1 PrependPath=1` so it's available system-wide and on your PATH.

### 2. Virtual environment
Creates a `.venv` folder in the project root using `python -m venv`. Skips this step if `.venv` already exists. Then activates the environment so all subsequent `pip` commands install into it, not globally.

### 3. Package installation
Upgrades `pip` to the latest version, then installs all dependencies in one call. Packages are grouped by purpose — see [Package List](#package-list) below.

### 4. Freeze requirements
Runs `pip freeze > requirements.txt` to snapshot the exact installed versions. This file is what other developers (or CI) use to reproduce the environment later.

### 5. Project folders
Creates the full directory structure under `data/`, `src/`, `models/`, `logs/`, etc. Uses `-Force` so it's safe to re-run without errors if folders already exist.

### 6. `__init__.py` files
Creates empty `__init__.py` files in every `src/` subdirectory so Python treats them as proper packages (required for imports like `from src.factors.momentum import ...`).

---

## Running Individual Steps

The script accepts flags to skip steps you don't need:

```powershell
# Skip Python check (if you know it's installed)
.\install.ps1 -SkipPython

# Only create folders, skip everything else
.\install.ps1 -SkipPython -SkipPackages

# Install packages only, skip folder creation
.\install.ps1 -SkipPython -SkipFolders
```

---

## VS Code Tasks

Open the task runner with `Ctrl+Shift+P` → `Tasks: Run Task`. Available tasks:

### Setup tasks

| Task | What it runs |
|------|-------------|
| `Setup: Full Project` | Runs `install.ps1` end-to-end. Also the default `Ctrl+Shift+B` build task. |
| `Setup: Create virtualenv` | `python -m venv .venv` only |
| `Setup: Install packages` | Activates venv and runs `pip install -r requirements.txt` |
| `Setup: Freeze requirements` | Activates venv and runs `pip freeze > requirements.txt` |
| `Setup: Create project folders` | Creates directory structure only |

### Development tasks

| Task | What it runs |
|------|-------------|
| `Dev: Activate venv in terminal` | Opens a new terminal panel with `.venv` already active |
| `Dev: Run tests` | `pytest tests/ -v --tb=short` |
| `Dev: Lint (flake8)` | `flake8 src/` |
| `Dev: Format (black)` | `black src/` |
| `Dev: Launch Jupyter` | `jupyter lab` pointed at the `notebooks/` folder |

---

## Reproducing the Environment (Other Developers)

Once `requirements.txt` exists (generated after the first install), anyone cloning the repo can reproduce the exact environment without re-downloading Python manually:

```powershell
# Create and activate venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install pinned versions
pip install -r requirements.txt
```

Or just run `install.ps1 -SkipPython` which does the same thing.

---

## Project Structure

```
your-project/
│
├── data/
│   ├── raw/
│   │   ├── wrds/
│   │   │   ├── crsp/          ← CRSP price/return data
│   │   │   ├── compustat/     ← Compustat fundamentals
│   │   │   └── ibes/          ← IBES analyst estimates
│   │   └── alpaca/
│   │       └── daily/         ← Alpaca daily OHLCV data
│   └── processed/
│       ├── factors/           ← Computed alpha factors
│       ├── events/            ← Event-driven signals
│       └── features/          ← ML feature matrices
│
├── src/
│   ├── data/                  ← Data ingestion & cleaning
│   ├── factors/               ← Factor calculation logic
│   ├── events/                ← Event detection
│   ├── ml/                    ← Model training & inference
│   ├── backtest/              ← Backtesting engine
│   ├── live/                  ← Live trading logic
│   └── utils/                 ← Shared helpers
│
├── models/
│   ├── trained/               ← Serialised model files
│   └── results/               ← Backtest outputs, metrics
│
├── notebooks/                 ← Jupyter notebooks for exploration
├── tests/                     ← pytest test suite
├── config/                    ← YAML config files
├── logs/                      ← Runtime logs
└── docker/                    ← Dockerfile and compose files
```

---

## Package List

| Group | Packages |
|-------|---------|
| Data & numerics | `numpy`, `polars`, `scipy`, `pyarrow`, `pandas-ta` |
| Machine learning | `scikit-learn`, `xgboost`, `lightgbm` |
| Data sources | `wrds`, `alpaca-trade-api`, `alpaca-py` |
| Azure | `azure-storage-blob`, `azure-identity`, `azure-monitor-query` |
| Async / networking | `websockets`, `aiohttp` |
| Technical analysis | `ta` |
| Backtesting | `backtrader`, `vectorbt` |
| Database | `sqlalchemy`, `psycopg2-binary` |
| Dashboards & API | `dash`, `plotly`, `flask` |
| Utilities | `python-dotenv`, `loguru`, `tqdm`, `joblib`, `schedule`, `pyyaml`, `click` |
| Notifications | `twilio`, `sendgrid` |
| Testing & quality | `pytest`, `pytest-asyncio`, `pytest-cov`, `black`, `flake8`, `mypy` |
| Notebooks | `jupyter`, `ipywidgets`, `ipykernel` |
| Infrastructure | `docker`, `gunicorn`, `watchdog` |

---

## Requirements

- Windows (the `.ps1` scripts are PowerShell-only)
- PowerShell execution policy must allow local scripts — if you see an error about execution policy, run this once in an admin PowerShell:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

- Internet access for the initial Python download and `pip install`
- ~2–3 GB disk space for the full virtual environment