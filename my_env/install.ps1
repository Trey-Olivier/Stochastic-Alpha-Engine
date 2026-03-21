# =========================
# Setup Python Project Script
# =========================

param(
    [string]$PythonVersion = "3.11.9",
    [switch]$SkipPython,
    [switch]$SkipPackages,
    [switch]$SkipFolders
)

$PythonInstaller = "$env:TEMP\python-$PythonVersion-amd64.exe"

# Always use the venv's own Python/pip executables directly.
# This avoids the "please run python -m pip" error and ensures
# we're not accidentally using the wrong system Python.
$VenvPython = ".\.venv\Scripts\python.exe"
$VenvPip    = ".\.venv\Scripts\pip.exe"

function Test-Python {
    try {
        $v = python --version 2>&1
        if ($v -like "*$PythonVersion*") { return $true }
        return $false
    } catch {
        return $false
    }
}

# ─────────────────────────────────────────
# 1. Python installation
# ─────────────────────────────────────────
if (-not $SkipPython) {
    if (-not (Test-Python)) {
        Write-Host "⬇  Downloading Python $PythonVersion..." -ForegroundColor Cyan
        Invoke-WebRequest -Uri "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe" -OutFile $PythonInstaller
        Write-Host "📦 Installing Python $PythonVersion..." -ForegroundColor Cyan
        Start-Process $PythonInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
    } else {
        Write-Host "✅ Python $PythonVersion already installed" -ForegroundColor Green
    }
    Write-Host "   System python: $(python --version)"
}

# ─────────────────────────────────────────
# 2. Virtual environment
# ─────────────────────────────────────────
if (-not (Test-Path ".venv")) {
    Write-Host "🐍 Creating virtual environment..." -ForegroundColor Cyan

    # If the system Python isn't 3.11.9, try the Python Launcher (py -3.11)
    if (-not (Test-Python)) {
        $pyLauncher = Get-Command "py" -ErrorAction SilentlyContinue
        if ($pyLauncher) {
            py -3.11 -m venv .venv
        } else {
            Write-Warning "Could not find Python $PythonVersion — venv may use a different version"
            python -m venv .venv
        }
    } else {
        python -m venv .venv
    }
} else {
    Write-Host "✅ .venv already exists" -ForegroundColor Green
}

$venvVer = & $VenvPython --version 2>&1
Write-Host "   Venv python:   $venvVer"

# ─────────────────────────────────────────
# 3. Packages
# ─────────────────────────────────────────
if (-not $SkipPackages) {
    $packages = @(
        # Data & numerics
        "numpy", "polars", "scipy", "pyarrow",
        # ML
        "scikit-learn", "xgboost", "lightgbm",
        # Data sources
        "wrds", "alpaca-trade-api", "alpaca-py",
        # Azure
        "azure-storage-blob", "azure-identity", "azure-monitor-query",
        # Async / networking
        "websockets", "aiohttp",
        # Technical analysis
        # Note: pandas-ta is abandoned and has no Python 3.11+ build — removed
        "ta",
        # Backtesting
        "backtrader", "vectorbt",
        # Database
        "sqlalchemy", "psycopg2-binary",
        # Dashboards / API
        "dash", "plotly", "flask",
        # Utilities
        "python-dotenv", "loguru", "tqdm", "joblib",
        "schedule", "pyyaml", "click",
        # Notifications
        "twilio", "sendgrid",
        # Testing & quality
        "pytest", "pytest-asyncio", "pytest-cov", "black", "flake8", "mypy",
        # Notebooks
        "jupyter", "ipywidgets", "ipykernel",
        # Infra
        "docker", "gunicorn", "watchdog"
    )

    Write-Host "📦 Upgrading pip..." -ForegroundColor Cyan
    & $VenvPython -m pip install --upgrade pip --quiet

    Write-Host "📦 Installing packages..." -ForegroundColor Cyan
    & $VenvPip install @packages

    Write-Host "📝 Freezing requirements.txt..." -ForegroundColor Cyan
    & $VenvPip freeze > requirements.txt
}

# ─────────────────────────────────────────
# 4. Project folders
# ─────────────────────────────────────────
if (-not $SkipFolders) {
    Write-Host "📁 Creating project structure..." -ForegroundColor Cyan

    $folders = @(
        "data/raw/wrds/crsp", "data/raw/wrds/compustat", "data/raw/wrds/ibes",
        "data/raw/alpaca/daily",
        "data/processed/factors", "data/processed/events", "data/processed/features",
        "src/data", "src/factors", "src/events", "src/ml",
        "src/backtest", "src/live", "src/utils",
        "models/trained", "models/results",
        "logs", "config", "tests", "notebooks", "docker", "scripts"
    )

    foreach ($f in $folders) {
        New-Item -ItemType Directory -Force -Path $f | Out-Null
    }

    $init_files = @(
        "src/__init__.py", "src/data/__init__.py", "src/factors/__init__.py",
        "src/events/__init__.py", "src/ml/__init__.py", "src/backtest/__init__.py",
        "src/live/__init__.py", "src/utils/__init__.py"
    )

    foreach ($f in $init_files) {
        if (-not (Test-Path $f)) { New-Item -ItemType File -Force -Path $f | Out-Null }
    }
}

Write-Host ""
Write-Host "✅ Setup complete! Run: .\.venv\Scripts\Activate.ps1" -ForegroundColor Green