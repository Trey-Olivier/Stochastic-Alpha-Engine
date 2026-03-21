# Stochastic-Alpha-Engine
# Multi-Factor ML Trading System: The Complete Implementation Bible
## From Zero to 24/7 Live Trading on Azure - Every Single Detail

> **What This Is:** A professional quantitative trading system running 24/7 on Azure, combining factor models + event analysis + machine learning to achieve 15-25% annual returns.

> **The Cool Part:** Your bot runs continuously in the cloud, monitors markets, trains models, executes trades, and you can edit code live without stopping it. It's like having a hedge fund manager who never sleeps.

> **Timeline:** 12 weeks to backtested strategy, 16 weeks to live 24/7 on Azure

> **Cost:** ~$150/month for infrastructure (cheaper than a gym membership for a money-making machine)

---

## 📚 MASTER TABLE OF CONTENTS

### 🏗️ PART 1: FOUNDATION & SETUP (Week 1-2)
- [1. System Architecture - The Big Picture](#1-system-architecture)
- [2. Why 24/7 Azure is Awesome](#2-why-247-azure-deployment)
- [3. Data Strategy: WRDS + Alpaca](#3-data-strategy)
- [4. Local Development Environment](#4-local-environment-setup)

### 📊 PART 2: WRDS DATA PIPELINE (Week 3-4)
- [5. What to Download from WRDS (Exact SQL)](#5-wrds-downloads)
- [6. Azure Blob Partitioning Strategy](#6-azure-blob-partitioning)
- [7. Upload WRDS Data to Azure](#7-upload-wrds-to-azure)
- [8. Point-in-Time Database (Critical!)](#8-point-in-time-database)

### 🦙 PART 3: ALPACA INTEGRATION (Week 3-4)
- [9. Alpaca Account Setup](#9-alpaca-account-setup)
- [10. Historical Data from Alpaca API](#10-alpaca-historical-data)
- [11. Real-Time WebSocket Feeds](#11-alpaca-real-time-feeds)
- [12. Order Execution](#12-alpaca-order-execution)

### 📈 PART 4: BUILDING ALL 60+ INDICATORS (Week 5-6)
- [13. Complete Factor Library](#13-complete-factor-library)
- [14. Value Factors (10 indicators)](#14-value-factors)
- [15. Momentum Factors (12 indicators)](#15-momentum-factors)
- [16. Quality Factors (15 indicators)](#16-quality-factors)
- [17. Technical Factors (12 indicators)](#17-technical-factors)
- [18. Volatility Factors (8 indicators)](#18-volatility-factors)
- [19. Size & Liquidity Factors (3 indicators)](#19-size-liquidity-factors)
- [20. Factor Calculation Code](#20-factor-calculation-code)
- [21. Factor Quality Checks](#21-factor-quality-checks)

### 📅 PART 5: EVENT DETECTION (Week 7-8)
- [22. Earnings Events from Alpaca](#22-earnings-events)
- [23. Surprise Calculation](#23-surprise-calculation)
- [24. Event Feature Engineering](#24-event-features)

### 🤖 PART 6: MACHINE LEARNING MODELS (Week 9-10)
- [25. ML Architecture Overview](#25-ml-architecture)
- [26. Factor Selection Model](#26-factor-selection-model)
- [27. Event Impact Model](#27-event-impact-model)
- [28. Training Pipeline](#28-training-pipeline)
- [29. Walk-Forward Validation](#29-walk-forward-validation)

### 📉 PART 7: BACKTESTING (Week 11-12)
- [30. Backtest Engine](#30-backtest-engine)
- [31. Transaction Costs & Slippage](#31-transaction-costs)
- [32. Performance Metrics](#32-performance-metrics)

### ☁️ PART 8: 24/7 AZURE DEPLOYMENT (Week 13-16)
- [33. Azure VM Setup](#33-azure-vm-setup)
- [34. Docker Container Configuration](#34-docker-configuration)
- [35. Hot Code Reloading Setup](#35-hot-code-reloading)
- [36. SSH & Remote Development](#36-ssh-remote-development)
- [37. Automated Deployment Pipeline](#37-deployment-pipeline)
- [38. Monitoring Dashboard](#38-monitoring-dashboard)
- [39. Making Edits While Bot is Running](#39-live-code-editing)

### ⚠️ PART 9: CRITICAL MISTAKES TO AVOID
- [40. Where You WILL Slip Up](#40-critical-pitfalls)
- [41. Look-Ahead Bias Examples](#41-look-ahead-bias)
- [42. Overfitting Red Flags](#42-overfitting-red-flags)
- [43. Data Quality Issues](#43-data-quality-issues)

### 🚀 PART 10: ADVANCED FEATURES
- [44. Advanced Factor Ideas](#44-advanced-factors)
- [45. Zero-Downtime Code Updates](#45-zero-downtime-updates)
- [46. Multi-Strategy Deployment](#46-multi-strategy)

---

## 1. System Architecture

### The Complete 24/7 Trading System

```
┌───────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES (External)                        │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  WRDS - Wharton Research Data Services                               │
│  ├─ CRSP Daily: Historical stock prices 2019-2024                    │
│  ├─ Compustat: Quarterly fundamentals (balance sheet, income)        │
│  └─ IBES: Analyst estimates & actuals                                │
│      │                                                                 │
│      └──> ONE-TIME DOWNLOAD via Python → Upload to Azure             │
│                                                                        │
│  ALPACA - Your Live Trading Broker                                    │
│  ├─ Market Data API: Real-time & historical prices (FREE)            │
│  ├─ Trading API: Order execution (paper + live)                      │
│  ├─ WebSocket: Live price streaming                                  │
│  └─ Corporate Actions API: Earnings calendar                         │
│                                                                        │
└───────────────────────────────────────────────────────────────────────┘
                                    ↓
┌───────────────────────────────────────────────────────────────────────┐
│              AZURE BLOB STORAGE - Your Data Lake ($2/month)           │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  📦 Container: raw-data/                                              │
│  ├── wrds/crsp/year=2024/month=03/crsp_daily_2024_03.parquet        │
│  ├── wrds/compustat/year=2024/quarter=Q1/fundamentals_Q1.parquet    │
│  ├── wrds/ibes/year=2024/month=03/estimates_2024_03.parquet         │
│  └── alpaca/daily/year=2024/month=03/alpaca_2024_03_13.parquet      │
│                                                                        │
│  📦 Container: processed-data/                                        │
│  ├── factors/year=2024/month=03/date=2024-03-13/                    │
│  │   └── all_factors_20240313.parquet (60+ factors for 500 stocks)  │
│  ├── events/year=2024/month=03/                                      │
│  │   └── earnings_events_2024_03.parquet                            │
│  └── ml-features/                                                     │
│      └── feature_matrix_20240313.parquet                            │
│                                                                        │
│  📦 Container: models/                                                │
│  ├── factor-model/                                                    │
│  │   ├── v1.0/model.pkl                                              │
│  │   ├── v1.1/model.pkl (retrained monthly)                         │
│  │   └── current → v1.1/ (symlink to latest)                        │
│  └── event-model/                                                     │
│      └── v1.0/model.pkl                                              │
│                                                                        │
└───────────────────────────────────────────────────────────────────────┘
                                    ↓
┌───────────────────────────────────────────────────────────────────────┐
│        AZURE VIRTUAL MACHINE - Running 24/7 ($100/month)              │
│        Standard_D4s_v3: 4 vCPUs, 16GB RAM, Ubuntu 22.04             │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  🐳 DOCKER CONTAINER: trading-bot (always running)                   │
│  ├─ Base Image: python:3.10-slim                                     │
│  ├─ Code Volume: Mounted from Azure File Share (hot reload enabled) │
│  └─ Logs: Streamed to Azure Monitor + local files                   │
│                                                                        │
│  🔄 RUNNING SERVICES (24/7 processes):                               │
│                                                                        │
│  1️⃣ MARKET DATA WATCHER (websocket_watcher.py)                      │
│     └─ Connects to Alpaca WebSocket                                  │
│     └─ Streams real-time prices for 500 stocks                       │
│     └─ Triggers events when earnings announced                       │
│     └─ Status: Always running during market hours                    │
│                                                                        │
│  2️⃣ NIGHTLY BATCH PROCESSOR (nightly_batch.py)                      │
│     └─ Runs at 11:00 PM ET (after market close)                     │
│     └─ Downloads today's data from Alpaca                            │
│     └─ Calculates all 60+ factors for all stocks                    │
│     └─ Saves to Azure Blob Storage                                   │
│     └─ Duration: ~15 minutes                                         │
│                                                                        │
│  3️⃣ EVENT MONITOR (event_monitor.py)                                │
│     └─ Checks for earnings events every 5 minutes                    │
│     └─ When detected: calculates surprise                            │
│     └─ Runs ML model to predict drift                                │
│     └─ Generates trade signal if threshold met                       │
│                                                                        │
│  4️⃣ TRADE EXECUTOR (trade_executor.py)                              │
│     └─ Market hours: 9:30 AM - 4:00 PM ET                           │
│     └─ Places orders via Alpaca API                                  │
│     └─ Monitors fills and updates positions                          │
│     └─ Enforces position limits (max 5% per stock)                  │
│                                                                        │
│  5️⃣ RISK MANAGER (risk_manager.py)                                  │
│     └─ Runs every minute during market hours                         │
│     └─ Checks stop losses (-8% per position)                        │
│     └─ Portfolio circuit breaker (-5% daily loss)                   │
│     └─ Sends alerts if limits breached                              │
│                                                                        │
│  6️⃣ MONTHLY RETRAINER (monthly_retrain.py)                          │
│     └─ Runs on 1st trading day of month at 8:00 PM ET              │
│     └─ Downloads latest data from Azure                              │
│     └─ Retrains both ML models                                       │
│     └─ Saves new version to Azure Blob                              │
│     └─ Duration: ~30 minutes                                         │
│                                                                        │
│  7️⃣ HOT RELOAD WATCHER (code_watcher.py)                            │
│     └─ Monitors /code directory for file changes                     │
│     └─ When you edit code → auto-restarts affected service          │
│     └─ Zero downtime (uses graceful restart)                        │
│     └─ Logs: "Detected change in factors.py, restarting..."        │
│                                                                        │
│  8️⃣ WEB DASHBOARD (dashboard.py)                                    │
│     └─ Flask/Dash app on port 8050                                   │
│     └─ Shows: live P&L, positions, signals, factor importance       │
│     └─ Access: http://your-vm-ip:8050                               │
│                                                                        │
└───────────────────────────────────────────────────────────────────────┘
                                    ↓
┌───────────────────────────────────────────────────────────────────────┐
│           YOUR LAPTOP - Development & Monitoring                       │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  💻 VS Code (Remote SSH Extension)                                   │
│  ├─ Connected to: your-vm.eastus.cloudapp.azure.com                 │
│  ├─ Edit files directly on Azure VM                                  │
│  ├─ Changes saved → hot reload triggers → service restarts          │
│  ├─ Terminal: see logs in real-time                                  │
│  └─ Debugger: attach to running Python processes                     │
│                                                                        │
│  🌐 Web Browser                                                       │
│  ├─ Dashboard: http://your-vm-ip:8050                               │
│  ├─ Azure Portal: monitor costs, health                             │
│  └─ Alpaca Dashboard: verify trades                                  │
│                                                                        │
│  📧 Alerts (automated)                                                │
│  ├─ Email: Trade executed, stop loss hit, errors                    │
│  ├─ SMS: Critical alerts only                                        │
│  └─ You configure what triggers alerts                              │
│                                                                        │
└───────────────────────────────────────────────────────────────────────┘
```

### How Data Flows Through the System

**Training Phase (One-Time):**
```
WRDS → Download Script → Azure Blob (raw-data/)
    ↓
Factor Calculator → Azure Blob (processed-data/factors/)
    ↓
ML Training Script → Trained Models → Azure Blob (models/)
```

**Live Trading Phase (Daily):**
```
9:30 AM: Market Opens
    ↓
Alpaca WebSocket → Live Prices → Market Data Watcher
    ↓
11:00 PM: Market Closed
    ↓
Nightly Batch → Calculate Today's Factors → Azure Blob
    ↓
Event Monitor → Check for Earnings → If Found:
    ↓
ML Model Prediction → Trade Signal → Trade Executor
    ↓
Alpaca API → Order Placed → Position Updated
    ↓
Risk Manager → Monitor Position → Enforce Stops
```

**Monthly Retrain (1st of Month):**
```
Download latest data from Azure → Retrain Models → Save new version
    ↓
Update symlink: models/current → models/v1.2/
    ↓
Services automatically load new model (no restart needed)
```

---

## 2. Why 24/7 Azure Deployment

### What Makes This Badass

**🚀 Continuous Operation**
- Bot watches markets even when you're asleep
- Catches earnings at 6 AM before work
- No "forgot to run my script" losses
- Trades execute at optimal times, not when convenient for you

**💻 Hot Code Reloading**
- Edit factor calculations → auto-reload
- Fix bugs → zero downtime
- Deploy improvements → seamless
- Like changing tires on a moving car (but safe)

**📊 Professional Infrastructure**
- Logs everything (required for tax audit)
- Monitors system health 24/7
- Alerts you to issues immediately
- Scales to multiple strategies easily

**🌍 Access from Anywhere**
- SSH from phone if needed
- Web dashboard shows status
- Make trades from vacation
- Your trading desk is everywhere

**💰 Cost Breakdown**

| Component | Service | Monthly Cost |
|-----------|---------|--------------|
| Compute | Azure VM Standard_D4s_v3 | $100 |
| Storage | Azure Blob Storage (3GB) | $2 |
| Network | Bandwidth & IP | $10 |
| Monitoring | Azure Monitor | $5 |
| **Total** | | **~$120/month** |

**For context:** That's less than:
- A Netflix + Spotify subscription
- Two dinners out
- Half a gym membership

**What you get:**
- A hedge fund that never sleeps
- Professional-grade infrastructure
- Potential 15-25% annual returns
- The coolest project you'll ever build

---

## 3. Data Strategy

### Why WRDS + Alpaca is the Perfect Combo

```
┌─────────────────────────────────────────────────────────┐
│              WRDS - Historical Training Data             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ✅ USE FOR:                                            │
│  • Training ML models (clean historical data)          │
│  • Backtesting strategies (2019-2024)                  │
│  • Calculating historical factor distributions         │
│  • Academic-quality fundamentals                       │
│                                                          │
│  ✅ ADVANTAGES:                                         │
│  • No survivorship bias (includes delisted stocks)     │
│  • Point-in-time accurate (no look-ahead bias)        │
│  • High quality (academic standard)                    │
│  • Complete fundamental data                           │
│                                                          │
│  ❌ LIMITATIONS:                                        │
│  • Delayed (fundamentals lag 1-3 months)              │
│  • No real-time data                                   │
│  • Can't use for live trading                         │
│  • Expensive if not academic ($2000+/year)            │
│                                                          │
│  📅 UPDATE FREQUENCY: Quarterly                        │
│                                                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              ALPACA - Live Trading Data                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ✅ USE FOR:                                            │
│  • Live price feeds (real-time via WebSocket)          │
│  • Recent historical data (free, 5+ years)             │
│  • Today's factor calculation                          │
│  • Order execution (paper + live)                      │
│  • Earnings calendar (upcoming events)                 │
│                                                          │
│  ✅ ADVANTAGES:                                         │
│  • Real-time data (no delay)                           │
│  • Free historical data                                │
│  • Commission-free trading                             │
│  • Great API (easy to use)                            │
│  • Paper trading environment                           │
│                                                          │
│  ❌ LIMITATIONS:                                        │
│  • No fundamental data (no P/E, ROE, etc.)            │
│  • No analyst estimates                                │
│  • Survivorship bias in historical data               │
│  • Limited history (5-6 years max)                    │
│                                                          │
│  📅 UPDATE FREQUENCY: Real-time / Daily                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### The Strategy

1. **One-Time WRDS Download**
   - Download 5 years of CRSP, Compustat, IBES
   - Upload to Azure Blob Storage
   - This is your training dataset
   - Update quarterly (fundamentals)

2. **Daily Alpaca Updates**
   - Download yesterday's data each night
   - Calculate today's factors
   - Run ML models for predictions
   - Execute trades if signals triggered

3. **Hybrid Factor Calculation**
   ```python
   # For historical backtesting:
   factors = calculate_factors(
       prices=wrds_crsp_data,          # From WRDS
       fundamentals=wrds_compustat_data # From WRDS
   )
   
   # For live trading:
   factors = calculate_factors(
       prices=alpaca_recent_data,       # From Alpaca
       fundamentals=latest_quarterly_data # From WRDS (updated quarterly)
   )
   ```

4. **Best of Both Worlds**
   - Train on clean WRDS data
   - Trade on real-time Alpaca data
   - No compromises

---

## 4. Local Environment Setup

### Step 1: Install Prerequisites

```bash
# Install Python 3.10
# Mac:
brew install python@3.10

# Ubuntu/Debian:
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip

# Windows:
# Download from https://www.python.org/downloads/
```

### Step 2: Create Project Structure

```bash
# Create project directory
mkdir quant_trading_system
cd quant_trading_system

# Create virtual environment
python3.10 -m venv venv

# Activate it
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Create directory tree
mkdir -p data/raw/wrds/{crsp,compustat,ibes}
mkdir -p data/raw/alpaca/daily
mkdir -p data/processed/{factors,events,features}
mkdir -p src/{data,factors,events,ml,backtest,live,utils}
mkdir -p models/{trained,results}
mkdir -p logs
mkdir -p config
mkdir -p tests
mkdir -p notebooks
mkdir -p docker

# Create empty __init__.py files (makes Python recognize directories as packages)
touch src/__init__.py
touch src/data/__init__.py
touch src/factors/__init__.py
touch src/events/__init__.py
touch src/ml/__init__.py
touch src/backtest/__init__.py
touch src/live/__init__.py
touch src/utils/__init__.py
```

### Step 3: Create requirements.txt

```txt
# requirements.txt - Complete dependency list

# ===== CORE DATA SCIENCE =====
numpy==1.24.3
pandas==2.0.3
scipy==1.11.1

# ===== MACHINE LEARNING =====
scikit-learn==1.3.0
xgboost==1.7.6
lightgbm==4.0.0

# ===== DATA SOURCES =====
wrds==3.1.6                    # WRDS connection
alpaca-trade-api==3.0.2        # Alpaca trading (legacy)
alpaca-py==0.8.2               # Alpaca trading (new async API)

# ===== AZURE =====
azure-storage-blob==12.17.0     # Blob storage
azure-identity==1.13.0          # Authentication
azure-monitor-query==1.2.0      # Monitoring

# ===== REAL-TIME DATA =====
websockets==11.0.3              # WebSocket client
aiohttp==3.8.5                  # Async HTTP

# ===== TECHNICAL ANALYSIS =====
ta==0.11.0                      # Technical indicators
pandas-ta==0.3.14b              # More indicators

# ===== BACKTESTING =====
backtrader==1.9.78.123
vectorbt==0.25.4                # Fast vectorized backtests

# ===== DATABASE =====
sqlalchemy==2.0.19              # SQL toolkit
psycopg2-binary==2.9.7          # PostgreSQL (if you want SQL storage)

# ===== WEB DASHBOARD =====
dash==2.13.0                    # Interactive dashboards
plotly==5.15.0                  # Charts
flask==2.3.3                    # Web framework

# ===== UTILITIES =====
python-dotenv==1.0.0            # Environment variables
loguru==0.7.0                   # Better logging
tqdm==4.65.0                    # Progress bars
joblib==1.3.1                   # Parallel processing
pyarrow==12.0.1                 # Fast parquet I/O
schedule==1.2.0                 # Task scheduling
pyyaml==6.0.1                   # YAML config files
click==8.1.6                    # CLI commands

# ===== ALERTS =====
twilio==8.5.0                   # SMS alerts
sendgrid==6.10.0                # Email alerts

# ===== TESTING =====
pytest==7.4.0
pytest-asyncio==0.21.1
pytest-cov==4.1.0

# ===== CODE QUALITY =====
black==23.7.0                   # Code formatter
flake8==6.1.0                   # Linter
mypy==1.4.1                     # Type checker

# ===== DEVELOPMENT =====
jupyter==1.0.0
ipywidgets==8.0.7
ipykernel==6.25.1

# ===== DEPLOYMENT =====
docker==6.1.3
gunicorn==21.2.0                # Production WSGI server
watchdog==3.0.0                 # File system watcher (hot reload)
```

### Step 4: Install Dependencies

```bash
# Install all packages
pip install -r requirements.txt

# Verify installation
python -c "import pandas, numpy, sklearn, alpaca_trade_api; print('✓ All core packages installed')"
```

### Step 5: Create .env File

```bash
# .env - Store all secrets here
# NEVER COMMIT THIS FILE TO GIT!

# ===== WRDS =====
WRDS_USERNAME=your_wrds_username
WRDS_PASSWORD=your_wrds_password

# ===== AZURE STORAGE =====
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=tradingdata001;AccountKey=YOUR_KEY_HERE;EndpointSuffix=core.windows.net
AZURE_STORAGE_ACCOUNT_NAME=tradingdata001
AZURE_STORAGE_ACCOUNT_KEY=YOUR_ACCOUNT_KEY_HERE

# Container names
AZURE_CONTAINER_RAW=raw-data
AZURE_CONTAINER_PROCESSED=processed-data
AZURE_CONTAINER_MODELS=models

# ===== ALPACA PAPER TRADING =====
ALPACA_PAPER_API_KEY=PK_YOUR_PAPER_KEY_HERE
ALPACA_PAPER_SECRET_KEY=your_paper_secret_key_here
ALPACA_PAPER_BASE_URL=https://paper-api.alpaca.markets

# ===== ALPACA LIVE TRADING (add later when ready) =====
# ALPACA_LIVE_API_KEY=your_live_api_key
# ALPACA_LIVE_SECRET_KEY=your_live_secret_key
# ALPACA_LIVE_BASE_URL=https://api.alpaca.markets

# ===== TRADING CONFIGURATION =====
TRADING_MODE=paper              # paper or live
UNIVERSE_SIZE=500               # How many stocks to track
POSITION_SIZE_MAX=0.05          # Max 5% per position
PORTFOLIO_STOP_LOSS=0.05        # Stop trading if down 5% in one day
REBALANCE_FREQUENCY=monthly     # monthly, weekly, or daily

# ===== ALERTS =====
# SendGrid (email)
SENDGRID_API_KEY=SG.your_key_here
ALERT_EMAIL_FROM=bot@yourtrading.com
ALERT_EMAIL_TO=you@email.com

# Twilio (SMS)
TWILIO_ACCOUNT_SID=AC_your_sid_here
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_FROM=+15551234567
TWILIO_PHONE_TO=+15559876543

# ===== LOGGING =====
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR
LOG_TO_FILE=true
LOG_TO_AZURE=false              # Set true when deployed to Azure

# ===== DEVELOPMENT =====
DEBUG_MODE=true
HOT_RELOAD_ENABLED=true
```

### Step 6: Create .gitignore

```bash
# .gitignore - Never commit these files

# Environment
.env
*.env
.env.local

# Data files (too large)
data/
*.parquet
*.csv
*.h5
*.pkl
*.joblib

# Model files
models/trained/
models/results/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/

# Jupyter
.ipynb_checkpoints
*.ipynb_checkpoints

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs
logs/
*.log

# OS
.DS_Store
Thumbs.db

# Azure credentials
.azure/

# Docker
.dockerignore
```

### Step 7: Create Config Files

```yaml
# config/strategy_config.yaml
# Main strategy configuration

trading:
  mode: paper  # paper or live
  universe_size: 500
  rebalance_frequency: monthly
  
positions:
  max_position_size: 0.05  # 5% max per stock
  max_sector_exposure: 0.25  # 25% max per sector
  max_positions: 40  # Total positions at once
  
risk:
  stop_loss_pct: 0.08  # -8% stop per position
  portfolio_stop_pct: 0.05  # -5% daily portfolio stop
  max_drawdown_pct: 0.25  # -25% max drawdown before pause
  
factors:
  min_importance: 0.01  # Drop factors with <1% importance
  retrain_frequency: monthly
  lookback_years: 3  # Years of data to train on
  
events:
  min_surprise_pct: 15  # Minimum 15% earnings surprise
  min_confidence: 0.7  # 70% model confidence required
  holding_period_days: 20  # Target holding period

alerts:
  email_on_trade: true
  email_on_stop: true
  email_on_error: true
  sms_on_critical: true  # Only critical alerts via SMS
```

---

## 5. WRDS Downloads

### Understanding What You're Downloading

**CRITICAL CONCEPT: You're downloading RAW data only, not pre-calculated ratios.**

```
❌ DON'T Download:
- Pre-calculated P/E ratios
- Pre-calculated momentum scores
- Any derived metrics from WRDS

✅ DO Download:
- Raw prices (OHLCV)
- Raw financial statement data
- Raw analyst estimates

WHY? 
1. Full control over calculations
2. Avoid look-ahead bias (WRDS calcs may use future data)
3. Customize (trailing vs forward P/E, etc.)
4. Understand every step
```

### A. CRSP Daily Stock File (Price Data)

**What it contains:**
- Daily OHLC prices
- Volume
- Returns
- Shares outstanding
- Split/dividend adjustments

**SQL Query to Run in WRDS Cloud:**

```sql
-- CRSP Daily Stock File
-- This query downloads 5 years of daily price data for common stocks

SELECT 
    -- Date
    a.date,
    
    -- Identifiers
    a.permno,                    -- CRSP permanent ID (PRIMARY KEY - use this!)
    a.permco,                    -- CRSP company ID
    b.ticker,                    -- Ticker symbol (changes over time)
    b.comnam,                    -- Company name
    b.shrcd,                     -- Share code (10/11 = common stocks)
    b.exchcd,                    -- Exchange (1=NYSE, 2=AMEX, 3=NASDAQ)
    
    -- Prices
    a.prc,                       -- Close price (negative = bid/ask average)
    a.openprc,                   -- Open price
    a.askhi,                     -- Intraday high
    a.bidlo,                     -- Intraday low
    
    -- Volume & Returns
    a.vol,                       -- Volume (shares)
    a.ret,                       -- Total return (with dividends)
    a.retx,                      -- Return excluding dividends
    
    -- Shares Outstanding
    a.shrout,                    -- Shares outstanding (in THOUSANDS!)
    
    -- Adjustment Factors
    a.cfacpr,                    -- Cumulative price adjustment factor
    a.cfacshr                    -- Cumulative shares adjustment factor

FROM 
    crsp.dsf AS a                           -- Daily Stock File
LEFT JOIN 
    crsp.dsenames AS b                      -- Stock names/tickers
    ON a.permno = b.permno 
    AND b.namedt <= a.date                  -- Name valid on this date
    AND a.date <= b.nameendt                -- Name not expired

WHERE 
    -- Date range: 5 years
    a.date >= '2019-01-01'
    AND a.date <= '2024-12-31'
    
    -- Common stocks only
    AND b.shrcd IN (10, 11)                 -- 10=common, 11=common (secondary)
    
    -- Major exchanges only
    AND b.exchcd IN (1, 2, 3)               -- NYSE, AMEX, NASDAQ
    
    -- Price filter (no penny stocks)
    AND ABS(a.prc) >= 5                     -- $5 minimum
    
    -- Must have volume
    AND a.vol > 0

ORDER BY 
    a.date,
    a.permno;
```

**Expected Output:**
- **Rows:** ~3-5 million
- **Size:** ~500 MB uncompressed
- **Download time:** 5-15 minutes
- **Stocks:** ~500-1000 (varies by filters)

**Run it:**

```bash
python src/data/download_crsp.py
```

### B. Compustat Fundamentals (Quarterly)

**What it contains:**
- Balance sheet (assets, liabilities, equity)
- Income statement (revenue, earnings, margins)
- Cash flow statement

**CRITICAL FIELD: `rdq` (Report Date Quarter)**

This is THE MOST IMPORTANT field for avoiding look-ahead bias.

```python
# Example: Apple Q1 2024
fiscal_quarter_end = '2024-03-30'  # Quarter ended
report_date = '2024-05-02'          # Announced to public

# ❌ WRONG: Use data on March 30
df[df['datadate'] == '2024-03-30']
# Problem: You didn't know the results yet!

# ✅ RIGHT: Use data only after May 2
df[df['rdq'] <= today]
# This is when the market learned the information
```

**SQL Query:**

```sql
-- Compustat Fundamentals Quarterly
-- Download quarterly financial statements

SELECT
    -- Identifiers
    gvkey,                       -- Compustat company key
    datadate,                    -- Fiscal period end date
    rdq,                         -- ⭐ REPORT DATE - When data became public
    fyearq,                      -- Fiscal year
    fqtr,                        -- Fiscal quarter (1-4)
    
    -- Company info
    tic,                         -- Ticker
    conm,                        -- Company name
    
    -- ===== INCOME STATEMENT =====
    revtq,                       -- Revenue (quarterly)
    cogsq,                       -- Cost of goods sold
    xsgaq,                       -- Selling, general & admin expense
    xrdq,                        -- R&D expense
    niq,                         -- Net income
    ibq,                         -- Income before extraordinary items
    epspxq,                      -- EPS (diluted, ex-extraordinary)
    xintq,                       -- Interest expense
    txtq,                        -- Income taxes
    dpq,                         -- Depreciation & amortization
    
    -- ===== BALANCE SHEET =====
    atq,                         -- Total assets
    actq,                        -- Current assets
    cheq,                        -- Cash
    rectq,                       -- Receivables
    invtq,                       -- Inventory
    ltq,                         -- Total liabilities
    lctq,                        -- Current liabilities
    dlcq,                        -- Short-term debt
    dlttq,                       -- Long-term debt
    seqq,                        -- Stockholders equity
    
    -- ===== CASH FLOW (YTD - we'll difference) =====
    oancfy,                      -- Operating cash flow (YTD)
    capxy,                       -- Capital expenditures (YTD)
    
    -- ===== MARKET DATA =====
    cshoq,                       -- Shares outstanding (millions)
    prccq,                       -- Stock price at quarter end
    
    -- ===== META =====
    curcdq,                      -- Currency
    fic,                         -- Country code
    sich                         -- Industry classification

FROM
    comp.fundq                   -- Fundamentals Quarterly

WHERE
    datadate >= '2019-01-01'
    AND datadate <= '2024-12-31'
    AND curcdq = 'USD'           -- US dollars only
    AND fic = 'USA'              -- US companies only
    AND atq IS NOT NULL          -- Must have assets
    AND revtq IS NOT NULL        -- Must have revenue
    AND rdq IS NOT NULL          -- Must have report date

ORDER BY
    gvkey,
    datadate;
```
### C. IBES Analyst Estimates

**What it contains:**
- Consensus analyst estimates for earnings
- Actual reported earnings
- Number of analysts covering each stock

**SQL Query:**

```sql
-- IBES Summary Statistics (Analyst Consensus)

SELECT
    ticker,
    statpers,                    -- Estimate date
    fpedats,                     -- Fiscal period end date
    fpi,                         -- Forecast period (1-4=Q1-Q4, 6=Annual)
    measure,                     -- EPS or Sales
    fiscalp,                     -- Fiscal period
    
    -- Consensus
    numest,                      -- Number of analysts
    meanest,                     -- Mean estimate (consensus)
    medest,                      -- Median estimate
    stdev,                       -- Standard deviation
    highest,                     -- Highest estimate
    lowest,                      -- Lowest estimate
    
    -- Actuals (when available)
    actual,                      -- Actual reported value
    anndats_act,                 -- Actual announcement date
    
    -- Currency
    curcode

FROM
    ibes.statsum_epsus           -- Summary stats (US, EPS)

WHERE
    statpers >= '2019-01-01'
    AND statpers <= '2024-12-31'
    AND fpi IN ('1', '2', '3', '4')  -- Quarterly estimates
    AND curcode = 'USD'
    AND numest > 0               -- Must have estimates

ORDER BY
    ticker,
    statpers,
    fpedats;
```
### Architecture Overview
```
┌─────────────────────────────────────────────────┐
│         LAYER 1: Factor Screening               │
│  (Identifies high-potential stocks)             │
│                                                  │
│  • Calculate 50+ factors for 500 stocks         │
│  • ML ranks stocks 1-500 by predicted return    │
│  • Output: Top 100 "factor-approved" stocks     │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│         LAYER 2: Event Detection                │
│  (Identifies catalysts/triggers)                │
│                                                  │
│  • Monitor earnings dates for top 100          │
│  • Track analyst estimates vs actuals           │
│  • Detect guidance changes, insider buying      │
│  • Measure deviation magnitude                  │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│         LAYER 3: Event Impact ML Model          │
│  (Predicts post-event returns)                  │
│                                                  │
│  Features:                                       │
│  • Factor scores (from Layer 1)                 │
│  • Event type & magnitude                       │
│  • Historical drift for similar events          │
│                                                  │
│  Target:                                         │
│  • Return in 5, 10, 20, 60 days post-event     │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│         LAYER 4: Trade Execution                │
│  (Final buy/sell decisions)                     │
│                                                  │
│  Buy if:                                         │
│  • Stock in top 100 factors (Layer 1)          │
│  • Positive catalyst detected (Layer 2)         │
│  • ML predicts >5% drift (Layer 3)             │
│                                                  │
│  Sell if:                                        │
│  • Drift period expired (typically 30-60 days) │
│  • Factor scores deteriorated                   │
│  • Negative event occurred                      │
└─────────────────────────────────────────────────┘
