# Alpha Factor Reference

The canonical reference for the 35 factors used in the model. Each entry covers the equation, what the signal actually means, data source, known pitfalls, and which precomputed pod columns it needs.

---

## Variable Conventions

| Symbol | Meaning |
|--------|---------|
| `P_t` | Adjusted close price at time t |
| `H_t` | Daily high |
| `L_t` | Daily low |
| `O_t` | Daily open |
| `V_t` | Share volume |
| `r_t` | Log return: `ln(P_t / P_{t-1})` |
| `SMA_N` | Simple moving average over N days |
| `EMA_N` | Exponential moving average, span N |
| `std(x, N)` | Rolling standard deviation over N days |
| `t-21` | ~1 month ago (21 trading days) |
| `t-63` | ~3 months ago |
| `t-126` | ~6 months ago |
| `t-252` | ~1 year ago |
| `ttm` | Trailing twelve months |
| `FCF` | Free cash flow = operating CFO − capex |
| `EV` | Enterprise value = market cap + net debt |

> All volatility is annualised: `daily_std × √252`
> All rolling operations are computed **per ticker**

---

## Factor Index

| # | Factor | Category | Source |
|---|--------|----------|--------|
| 1 | `ret_12m_skip1m` | Momentum | Price |
| 2 | `ret_1m` | Momentum | Price |
| 3 | `mom_12m_minus_6m` | Momentum | Price |
| 4 | `price_vs_200d_ma` | Momentum | Price |
| 5 | `ma_50_vs_200` | Momentum | Price |
| 6 | `vol_20d` | Volatility | Price |
| 7 | `downside_vol_20d` | Volatility | Price |
| 8 | `vol_ratio_20_60` | Volatility | Price |
| 9 | `beta_1y` | Volatility | Price + Market |
| 10 | `max_drawdown_60d` | Volatility | Price |
| 11 | `amihud_illiquidity` | Liquidity | Price + Volume |
| 12 | `avg_dollar_volume_20d` | Liquidity | Price + Volume |
| 13 | `bid_ask_spread_proxy` | Liquidity | Price |
| 14 | `log_market_cap` | Size | Price + Shares |
| 15 | `book_to_market` | Value | Compustat |
| 16 | `earnings_yield` | Value | Compustat |
| 17 | `ebitda_to_ev` | Value | Compustat |
| 18 | `free_cashflow_yield` | Value | Compustat |
| 19 | `gross_profitability` | Quality | Compustat |
| 20 | `ROE` | Quality | Compustat |
| 21 | `sloan_accruals` | Quality | Compustat |
| 22 | `debt_to_equity` | Quality | Compustat |
| 23 | `revenue_growth` | Growth | Compustat |
| 24 | `earnings_growth` | Growth | Compustat |
| 25 | `RSI_14` | Technical | Price |
| 26 | `MACD_histogram` | Technical | Price |
| 27 | `bollinger_bandwidth` | Technical | Price |
| 28 | `distance_52w_high` | Technical | Price |
| 29 | `earnings_surprise` | Analyst | IBES |
| 30 | `earnings_revision_30d` | Analyst | IBES |
| 31 | `analyst_dispersion` | Analyst | IBES |
| 32 | `post_earnings_drift` | Event | Price + IBES |
| 33 | `insider_buy_sell_ratio` | Event | SEC Form 4 |
| 34 | `VaR_95` | Volatility | Price |
| 35 | `idiosyncratic_vol` | Volatility | Price + Market |

---

---

# Momentum Factors

---

## 1. `ret_12m_skip1m` — Classic Academic Momentum

**Equation**
```
(P_{t-21} - P_{t-252}) / P_{t-252}
```

**What it measures**
12-month price return, excluding the most recent month. The skip is critical — the most recent month has a reversal effect (short-term mean reversion) that would partially cancel the signal if included. This is the Jegadeesh-Titman (1993) momentum factor, one of the most replicated findings in finance.

**Interpretation**
- High value → strong past winner → expect continued outperformance
- Low value → past loser → expect continued underperformance
- Works best held for 3–12 months; decays and reverses beyond ~18 months

**Pitfalls**
- Crashes hard in sharp reversals (March 2009, March 2020) — momentum strategies can lose 30–50% in a single month during a crash-and-rebound
- Requires careful turnover management; high-momentum stocks churn frequently
- Weaker in small caps due to illiquidity

**Data source** — Alpaca daily OHLCV

**Pod columns needed**
```
P_21, P_252
```

---

## 2. `ret_1m` — Short-Term Return (Reversal Signal)

**Equation**
```
(P_t - P_{t-21}) / P_{t-21}
```

**What it measures**
The most recent month's return. Used as a **reversal** signal — high recent return predicts short-term underperformance, and vice versa. This is the opposite of momentum, operating at a shorter horizon.

**Interpretation**
- When used as a standalone factor, a **low** value is bullish (mean reversion)
- When combined with `ret_12m_skip1m`, a high value here dampens the momentum signal (the skip window handles this)

**Pitfalls**
- Very noisy at the individual stock level
- High transaction costs if traded directly; better used as a composite component
- Bid-ask bounce inflates reversal signal in illiquid stocks

**Data source** — Alpaca daily OHLCV

**Pod columns needed**
```
P_21
```

---

## 3. `mom_12m_minus_6m` — Momentum Acceleration

**Equation**
```
ret_12m - ret_6m
= (P_t - P_{t-252}) / P_{t-252}  -  (P_t - P_{t-126}) / P_{t-126}
```

**What it measures**
The difference between long-term and medium-term momentum. A positive value means the stock has been accelerating — most of its yearly gain came in the first half of the window. Negative means recent deceleration.

**Interpretation**
- Positive → momentum is building → augments the main momentum signal
- Negative → momentum is fading → fade or reduce position

**Pitfalls**
- Second derivative of a noisy signal — amplifies noise
- Works better as a composite weight than a standalone factor

**Data source** — Alpaca daily OHLCV

**Pod columns needed**
```
P_126, P_252
```

---

## 4. `price_vs_200d_ma` — Distance from Long-Term Trend

**Equation**
```
(P_t - SMA_200) / SMA_200
```

**What it measures**
How far the current price is above or below its 200-day moving average, expressed as a fraction. A proxy for whether the stock is in a long-term uptrend or downtrend.

**Interpretation**
- Positive → price above trend → bullish regime
- Negative → price below trend → bearish regime
- Often used as a filter: only take long signals when this is positive

**Pitfalls**
- Lags significantly — 200-day MA is slow by design
- Generates false signals in choppy, range-bound markets
- Highly correlated with `ma_50_vs_200`; don't double-count both in a linear model without orthogonalising

**Data source** — Alpaca daily OHLCV

**Pod columns needed**
```
SMA_200
```

---

## 5. `ma_50_vs_200` — Golden / Death Cross

**Equation**
```
(SMA_50 - SMA_200) / SMA_200
```

**What it measures**
The relationship between medium-term and long-term trend. A positive value (50-day above 200-day) is the "golden cross" — widely watched as a bullish trend confirmation. Negative is the "death cross."

**Interpretation**
- Positive → medium-term trend above long-term → sustained uptrend
- Negative → medium-term below long-term → downtrend or transition
- Crossover events are lagging signals — the value level is more useful as a continuous factor than the crossover event itself

**Pitfalls**
- Extremely correlated with `price_vs_200d_ma` — they encode nearly the same information
- Use one or the other in a regression, not both, unless you explicitly want the crossover relationship

**Data source** — Alpaca daily OHLCV

**Pod columns needed**
```
SMA_50, SMA_200
```

---

---

# Volatility Factors

---

## 6. `vol_20d` — 20-Day Realised Volatility

**Equation**
```
std(r_t, 20) × √252
```

**What it measures**
Annualised standard deviation of daily log returns over the past 20 trading days. The core volatility measure — captures current risk level.

**Interpretation**
- High → stock is moving a lot → higher risk, often lower future returns (low-vol anomaly)
- Low → stock is calm → historically associated with better risk-adjusted returns
- The low-volatility anomaly is one of the most persistent anomalies: low-vol stocks outperform on a risk-adjusted basis

**Pitfalls**
- 20 days is short — heavily influenced by a single earnings move or news event
- Should be normalised cross-sectionally; raw vol levels vary enormously across sectors
- Correlated with size (small caps are more volatile)

**Data source** — Alpaca daily OHLCV

**Pod columns needed**
```
std_r_20
```

---

## 7. `downside_vol_20d` — Downside Volatility

**Equation**
```
std(min(r_t, 0), 20) × √252
```

**What it measures**
Standard deviation of negative returns only. Captures the asymmetric risk that standard deviation misses — a stock that only moves violently downward looks identical to one that moves violently upward in `vol_20d`, but very different here.

**Interpretation**
- High downside vol relative to total vol → negatively skewed returns → more dangerous than total vol suggests
- Used in the Sortino ratio: `mean_return / downside_vol`

**Pitfalls**
- Very noisy with only 20 days of data — many days contribute zero (all positive returns)
- Consider a longer window (60d) if using standalone

**Data source** — Alpaca daily OHLCV

**Pod columns needed**
```
std_r_down_20
```

---

## 8. `vol_ratio_20_60` — Volatility Regime Indicator

**Equation**
```
vol_20d / vol_60d
= std(r, 20) / std(r, 60)
```

**What it measures**
Whether short-term volatility is elevated relative to medium-term. Captures volatility regime changes — expanding or contracting risk.

**Interpretation**
- > 1 → vol is expanding → uncertainty increasing, often precedes drawdowns
- < 1 → vol is contracting → calm period, often precedes breakouts
- Useful as a risk filter: reduce exposure when ratio spikes above 1.5

**Pitfalls**
- Ratio is unstable near earnings events — a single big move distorts the 20-day window
- Not a directional signal on its own; combine with trend signals

**Data source** — Alpaca daily OHLCV

**Pod columns needed**
```
std_r_20, std_r_60
```

---

## 9. `beta_1y` — Market Beta

**Equation**
```
cov(r_stock, r_market) / var(r_market)   over 252 days
```

**What it measures**
Sensitivity of the stock's returns to the broad market (S&P 500). A beta of 1.2 means the stock moves 1.2% for every 1% market move on average.

**Interpretation**
- > 1 → amplifies market moves → higher risk in downturns, higher reward in rallies
- < 1 → defensive → cushions drawdowns
- Low-beta stocks have historically earned higher risk-adjusted returns (the beta anomaly)
- Used as a risk control: target portfolio beta = 1 for market-neutral

**Pitfalls**
- Beta is unstable — it changes with market regimes
- 252-day window includes stale data; some practitioners use 60-day or shrink toward 1
- Requires daily SPY or SPX returns joined to your universe

**Data source** — Alpaca (stock + SPY daily returns)

**Pod columns needed**
```
std_r_252, r   (plus SPY r joined as r_market)
```

---

## 10. `max_drawdown_60d` — Recent Maximum Drawdown

**Equation**
```
min((P_t - max(P_{t-60:t})) / max(P_{t-60:t}))
```

**What it measures**
The worst peak-to-trough decline over the past 60 trading days. Captures tail risk and recent stress in a way that standard deviation doesn't.

**Interpretation**
- Deep drawdown → stock has been under significant selling pressure
- As a factor: large recent drawdown can signal either distress (avoid) or mean reversion opportunity (buy) depending on your strategy

**Pitfalls**
- Path-dependent — same return can produce very different drawdowns
- A 60-day window is short; a single bad month dominates
- Combine with vol and momentum to distinguish "falling knife" from "temporary dip"

**Data source** — Alpaca daily OHLCV

**Pod columns needed**
```
high_60
```

---

## 11. `VaR_95` — Value at Risk (95%)

**Equation**
```
percentile(r, 5)   over 252 days
```

**What it measures**
The 5th percentile of daily returns over the past year — the loss you'd expect to exceed only 5% of trading days. A forward-looking risk estimate based on historical distribution.

**Interpretation**
- More negative → fatter left tail → more dangerous stock
- Complements vol: two stocks can have the same vol but very different VaR if one has a fat left tail

**Pitfalls**
- Historical VaR assumes the future looks like the past — breaks down in regime changes
- 252 days may not include a meaningful stress period for many stocks
- CVaR (expected shortfall) is a better risk measure but requires more data

**Data source** — Alpaca daily OHLCV

**Pod columns needed**
```
std_r_252, r   (percentile computed over rolling 252-day window)
```

---

## 12. `idiosyncratic_vol` — Stock-Specific Volatility

**Equation**
```
std(r_stock - β × r_market)   over rolling window
```

**What it measures**
The volatility that cannot be explained by market moves — pure company-specific risk. After removing market beta, the residual vol captures earnings uncertainty, news risk, and idiosyncratic events.

**Interpretation**
- High idiosyncratic vol → stock moves on its own news, not just market moves
- Low idiosyncratic vol → stock tracks the market closely
- As a factor: high idiosyncratic vol predicts lower future returns (investors demand compensation but don't get it — the idiosyncratic vol puzzle)

**Pitfalls**
- Requires beta to be estimated first
- Sensitive to the beta estimation window
- Correlated with size and analyst coverage

**Data source** — Alpaca (stock + SPY)

**Pod columns needed**
```
r, r_market (SPY), beta_1y (precomputed)
```

---

---

# Liquidity Factors

---

## 13. `amihud_illiquidity` — Price Impact per Dollar Traded

**Equation**
```
mean(|r_t| / (P_t × V_t), 20) × 10⁶
```

**What it measures**
How much price moves per dollar of trading volume. A high value means a small trade moves the price a lot — the stock is illiquid. Multiplied by 10⁶ to put it in a readable range.

**Interpretation**
- High → illiquid → hard to trade without moving the price
- Low → liquid → large orders can be executed cheaply
- Illiquid stocks earn an illiquidity premium (higher expected returns) but are expensive to trade in practice

**Pitfalls**
- Extreme outliers on days with very low volume — winsorise before using
- Sensitive to price level; normalisation by 10⁶ is conventional but arbitrary
- Use log(amihud) in models to reduce skew

**Data source** — Alpaca daily OHLCV

**Pod columns needed**
```
abs_r, dv, amihud_20
```

---

## 14. `avg_dollar_volume_20d` — Average Daily Dollar Volume

**Equation**
```
mean(P_t × V_t, 20)
```

**What it measures**
Average daily liquidity in dollar terms over the past month. Used primarily as a **filter** (exclude stocks below a threshold) and as a size-adjusted liquidity measure.

**Interpretation**
- High → very liquid → lower transaction costs, more institutional interest
- Low → illiquid → higher costs, limits position sizing
- Typical filter: require > $1M/day for small portfolios, > $10M/day for larger

**Pitfalls**
- Highly correlated with market cap — large stocks are liquid almost by definition
- Winsorise at the top; mega-cap stocks skew the distribution

**Data source** — Alpaca daily OHLCV

**Pod columns needed**
```
dv_20
```

---

## 15. `bid_ask_spread_proxy` — Estimated Transaction Cost

**Equation**
```
2 × (H_t - L_t) / (H_t + L_t)
```

**What it measures**
An estimate of the bid-ask spread using the daily high-low range. A proxy for transaction cost when actual bid-ask data isn't available at EOD.

**Interpretation**
- High → wide spread → expensive to trade → requires larger alpha to be profitable
- Low → tight spread → cheap to trade → more strategies are viable

**Pitfalls**
- High-low range captures intraday volatility as well as the spread — conflates two things
- More accurate on low-volatility days; meaningless on days with large directional moves
- Better than nothing for EOD data, but actual bid-ask from a level 2 feed is preferable

**Data source** — Alpaca daily OHLCV

**Pod columns needed**
```
hl   (high - low, precomputed in pod)
```

---

---

# Size Factor

---

## 16. `log_market_cap` — Log Market Capitalisation

**Equation**
```
ln(P_t × shares_outstanding)
```

**What it measures**
The log of total market value. Log-transformed to reduce skew — market cap is extremely right-skewed (a few mega-caps vs. thousands of small companies). The core size factor in Fama-French.

**Interpretation**
- High → large cap → lower expected returns (size premium) but safer, more liquid
- Low → small cap → higher expected returns historically but higher risk and costs
- The size premium has weakened significantly post-2000; use mainly as a control variable

**Pitfalls**
- Must be recomputed daily as price changes
- Highly correlated with liquidity factors — size and liquidity are largely the same thing
- Use as a control/neutralisation variable in your model rather than a pure alpha signal

**Data source** — Alpaca (price) + shares outstanding

**Pod columns needed**
```
market_cap   (P_t × shares_outstanding, computed in pod)
```

---

---

# Value Factors

---

## 17. `book_to_market` — Book Value to Market Cap

**Equation**
```
book_equity / market_cap
```

**What it measures**
The ratio of accounting book value to market value. The core Fama-French HML (High Minus Low) value factor. High B/M means the market values the company cheaply relative to its balance sheet.

**Interpretation**
- High → value stock → market is pricing in distress or pessimism
- Low → growth stock → market prices in high future earnings
- Value premium historically ~4%/year but has had long drawdown periods (2010–2020)

**Pitfalls**
- Book value is a backward-looking accounting construct — intangibles (brands, software) are largely excluded, making B/M misleading for tech companies
- Quarterly frequency — forward-fill to daily
- Use alongside profitability to distinguish "cheap and good" from "cheap and broken" (value trap)

**Data source** — Compustat quarterly

**Pod columns needed**
```
market_cap   (daily, from pod)
book_equity  (quarterly, forward-filled join)
```

---

## 18. `earnings_yield` — Earnings Relative to Price

**Equation**
```
EPS_ttm / P_t
```

**What it measures**
Trailing 12-month earnings per share divided by price. The inverse of the P/E ratio, expressed as a yield. Analogous to the yield on a bond — what you "earn" per dollar invested.

**Interpretation**
- High → cheap on earnings → value signal
- Low → expensive → growth or distress
- More intuitive than P/E for cross-sectional ranking (avoids negative P/E issues)

**Pitfalls**
- TTM EPS is backward-looking; a company in decline looks cheap on trailing earnings
- Negative earnings make the ratio meaningless — winsorise or exclude
- Forward P/E is more predictive but requires consensus estimates (IBES)

**Data source** — Compustat (EPS ttm)

**Pod columns needed**
```
EPS_ttm  (quarterly, forward-filled)
```

---

## 19. `ebitda_to_ev` — EBITDA Yield on Enterprise Value

**Equation**
```
EBITDA / (market_cap + net_debt)
```

**What it measures**
Operating earnings relative to the total capital structure (equity + debt). Capital-structure-neutral — two companies with identical operations but different leverage look the same on this metric.

**Interpretation**
- High → cheap relative to operating earnings → value signal
- Better than P/E for comparing companies across industries with different capital structures (e.g. airlines vs. software)
- EV/EBITDA is the standard M&A valuation multiple; high values here mean the market is pricing the business cheaply relative to what an acquirer would pay

**Pitfalls**
- EBITDA excludes capex — misleading for capital-intensive businesses (utilities, telecoms)
- Debt changes quarterly; net_debt must be kept current
- Negative EBITDA makes the ratio meaningless

**Data source** — Compustat

**Pod columns needed**
```
market_cap      (daily pod)
EBITDA_ttm      (quarterly, forward-filled)
net_debt        (quarterly, forward-filled)
```

---

## 20. `free_cashflow_yield` — FCF per Dollar of Market Cap

**Equation**
```
FCF / market_cap
= (operating_cashflow - capex) / market_cap
```

**What it measures**
How much actual cash the business generates relative to its market value. FCF is harder to manipulate than earnings — it's what's left after maintaining and growing the business.

**Interpretation**
- High → business generates lots of cash relative to price → strong value signal
- More reliable than earnings yield because cash flow is harder to manipulate than net income (see Sloan accruals)
- Buffett's preferred valuation metric

**Pitfalls**
- Lumpy for capital-intensive businesses — a large one-time capex distorts the annual figure
- Negative FCF is normal for early-stage growth companies — not necessarily a bad sign
- Use TTM or average of last 2 years to smooth lumpiness

**Data source** — Compustat (operating cash flow, capex)

**Pod columns needed**
```
market_cap          (daily pod)
operating_cashflow  (quarterly ttm, forward-filled)
capex               (quarterly ttm, forward-filled)
```

---

---

# Quality Factors

---

## 21. `gross_profitability` — Novy-Marx Quality Factor

**Equation**
```
(revenue - COGS) / total_assets
```

**What it measures**
Gross profit scaled by assets. The Novy-Marx (2013) profitability factor — one of the most robust quality signals in academic literature. Gross profit is used (not net income) because it's less subject to managerial manipulation and captures the core economic productivity of the business.

**Interpretation**
- High → highly profitable business relative to its asset base → quality signal
- Combines well with value: high gross profitability + high B/M = "quality value"
- Negatively correlated with B/M — growth stocks tend to be more profitable — so adding profitability to a value model improves performance

**Pitfalls**
- Gross profit excludes SG&A, R&D — a company spending heavily on future growth looks less profitable here
- Industry-specific: retail has thin gross margins, software has very high margins — normalise within industry

**Data source** — Compustat annual

**Pod columns needed**
```
revenue_ttm   (annual/quarterly, forward-filled)
COGS_ttm      (annual/quarterly, forward-filled)
total_assets  (annual/quarterly, forward-filled)
```

---

## 22. `ROE` — Return on Equity

**Equation**
```
net_income / book_equity
```

**What it measures**
How efficiently management generates profit from shareholders' capital. The most widely used profitability metric.

**Interpretation**
- High → management is generating strong returns on the capital entrusted to them
- Combine with leverage awareness: high ROE driven by high debt is less impressive than high ROE from genuine operational efficiency
- ROE > cost of equity = value creation; ROE < cost of equity = value destruction

**Pitfalls**
- Can be inflated by leverage (debt increases ROE mechanically) or share buybacks (reduces equity denominator)
- Negative equity (from buybacks or losses) produces meaningless ROE
- TTM smoothing recommended — single quarters are noisy

**Data source** — Compustat

**Pod columns needed**
```
net_income_ttm  (quarterly ttm, forward-filled)
book_equity     (quarterly, forward-filled)
```

---

## 23. `sloan_accruals` — Earnings Quality

**Equation**
```
(net_income - CFO - CFI) / total_assets
```
where CFO = operating cash flow, CFI = investing cash flow

**What it measures**
The proportion of earnings that comes from accruals rather than cash. High accruals mean earnings are supported by accounting adjustments, not actual cash generation. Sloan (1996) showed high-accrual firms subsequently underperform — the market overpays for accrual-based earnings.

**Interpretation**
- Low (near zero or negative) → earnings backed by cash → high quality
- High → earnings driven by accruals → red flag, expect mean reversion
- One of the most reliable quality signals; the "earnings quality" factor

**Pitfalls**
- Requires all three cash flow statement items — data gaps are common
- Acquisition-heavy companies naturally have high accruals (goodwill, intangibles)
- Annual frequency is standard; quarterly is noisy

**Data source** — Compustat (income statement + cash flow statement)

**Pod columns needed**
```
net_income_ttm  (annual, forward-filled)
CFO_ttm         (annual, forward-filled)
CFI_ttm         (annual, forward-filled)
total_assets    (annual, forward-filled)
```

---

## 24. `debt_to_equity` — Leverage

**Equation**
```
total_debt / book_equity
```

**What it measures**
How much of the company is financed by debt vs. equity. A measure of financial risk — high leverage amplifies both gains and losses and increases bankruptcy risk.

**Interpretation**
- High → more levered → higher risk, higher sensitivity to interest rates
- Low → conservative balance sheet → more resilient in downturns
- As a factor: low leverage predicts modestly better returns (firms that don't need debt are higher quality)

**Pitfalls**
- Industry-specific: banks and utilities are legitimately highly leveraged — normalise within industry
- Book equity can be negative (makes ratio meaningless) — use debt-to-assets as backup
- Net debt (debt minus cash) is more informative than gross debt

**Data source** — Compustat

**Pod columns needed**
```
total_debt   (quarterly, forward-filled)
book_equity  (quarterly, forward-filled)
```

---

---

# Growth Factors

---

## 25. `revenue_growth` — Year-over-Year Revenue Growth

**Equation**
```
(revenue_t - revenue_{t-4q}) / revenue_{t-4q}
```

**What it measures**
Year-over-year top-line growth, comparing the most recent quarter to the same quarter one year ago (avoids seasonality distortion). Captures business momentum at the fundamental level.

**Interpretation**
- High → business is expanding → growth signal, often associated with price momentum
- Decelerating growth is often more informative than the level — a company going from 30% to 15% growth is often a sell even though 15% is strong in absolute terms

**Pitfalls**
- Acquisitions can spike revenue artificially — check for M&A activity
- Same-quarter comparison removes seasonality but one bad quarter a year ago flatters the current number
- Revenue growth without margin expansion is less valuable

**Data source** — Compustat quarterly

**Pod columns needed**
```
revenue_q       (most recent quarter)
revenue_q_4ago  (same quarter 1 year prior)
```

---

## 26. `earnings_growth` — Year-over-Year EPS Growth

**Equation**
```
(EPS_t - EPS_{t-4q}) / |EPS_{t-4q}|
```

**What it measures**
Year-over-year earnings per share growth. Absolute value in the denominator handles sign changes (e.g. going from a small loss to a profit).

**Interpretation**
- High → earnings expanding → fundamental momentum
- Combine with revenue growth to check whether earnings growth is driven by real growth or cost-cutting

**Pitfalls**
- EPS is easily manipulated (buybacks reduce share count, boosting EPS without revenue growth)
- Sign changes make the ratio unstable — winsorise aggressively
- One-time items (write-offs, asset sales) distort quarterly figures; use adjusted EPS from IBES if available

**Data source** — Compustat / IBES

**Pod columns needed**
```
EPS_q       (most recent quarter diluted EPS)
EPS_q_4ago  (same quarter 1 year prior)
```

---

---

# Technical Factors

---

## 27. `RSI_14` — Relative Strength Index

**Equation**
```
100 - 100 / (1 + RS)
where RS = avg_gain_14 / avg_loss_14
avg_gain = EMA(max(r_1d, 0), 14)
avg_loss = EMA(max(-r_1d, 0), 14)
```

**What it measures**
A bounded [0, 100] oscillator measuring the ratio of recent gains to recent losses. The most widely used momentum/mean-reversion oscillator.

**Interpretation**
- > 70 → overbought → short-term mean reversion likely
- < 30 → oversold → potential bounce
- In a trend-following strategy, RSI > 50 is used as a bullish filter
- In a mean-reversion strategy, extreme RSI levels are the signal

**Pitfalls**
- Overbought/oversold levels are not symmetric — stocks can stay overbought for months in strong uptrends
- The 14-day period is conventional but arbitrary; test sensitivity
- Don't use in isolation — RSI 30 in a downtrend is a falling knife, not a buy signal

**Data source** — Alpaca daily OHLCV

**Pod columns needed**
```
avg_gain_14, avg_loss_14
```

---

## 28. `MACD_histogram` — Momentum of Momentum

**Equation**
```
MACD       = EMA_12 - EMA_26
MACD_signal = EMA_9(MACD)
MACD_hist  = MACD - MACD_signal
```

**What it measures**
The difference between the MACD line and its signal line. Captures whether short-term momentum is accelerating or decelerating relative to its own trend.

**Interpretation**
- Positive and increasing → momentum building → bullish
- Positive and decreasing → momentum fading → early warning
- Crossing zero from below → trend turning bullish
- Crossing zero from above → trend turning bearish

**Pitfalls**
- Three layers of smoothing make this a very lagging indicator
- Generates many false signals in choppy markets
- Better used as a continuous factor in a model than as a simple crossover rule

**Data source** — Alpaca daily OHLCV

**Pod columns needed**
```
EMA_12, EMA_26, MACD, MACD_signal, MACD_hist
```

---

## 29. `bollinger_bandwidth` — Volatility Squeeze Indicator

**Equation**
```
BB_upper = SMA_20 + 2 × std(P, 20)
BB_lower = SMA_20 - 2 × std(P, 20)
bandwidth = (BB_upper - BB_lower) / SMA_20
```

**What it measures**
The width of Bollinger Bands relative to price. Low bandwidth = price is in a tight range (squeeze). High bandwidth = price is in a wide, volatile range.

**Interpretation**
- Low (squeeze) → volatility contraction → often precedes a large breakout in either direction
- High → volatility expansion → trend is underway, or a large move has already happened
- Use the squeeze as a setup, then wait for directional confirmation before entering

**Pitfalls**
- Bandwidth tells you a move is coming, not which direction
- Squeezes can persist for weeks before resolving
- Combine with momentum factors to determine likely breakout direction

**Data source** — Alpaca daily OHLCV

**Pod columns needed**
```
SMA_20, std_P_20, BB_upper, BB_lower, BB_width
```

---

## 30. `distance_52w_high` — Proximity to 52-Week High

**Equation**
```
(P_t - max(P_{t-252:t})) / max(P_{t-252:t})
```

**What it measures**
How far the current price is below the 52-week high, expressed as a fraction (always ≤ 0). George and Hwang (2004) showed this is actually a stronger momentum predictor than standard return-based momentum.

**Interpretation**
- Near zero → price near 52-week high → strong momentum signal
- Very negative → price far from 52-week high → either value opportunity or distress
- The intuition: investors anchor to the 52-week high and are reluctant to buy above it, creating underreaction that eventually corrects

**Pitfalls**
- Conflates momentum and value — a stock near its 52-week high could be there because it crashed a year ago and just recovered
- Sensitive to the exact 252-day window
- Combine with volume confirmation

**Data source** — Alpaca daily OHLCV

**Pod columns needed**
```
high_252
```

---

---

# Analyst Factors

---

## 31. `earnings_surprise` — Actual vs. Consensus EPS

**Equation**
```
(EPS_actual - EPS_consensus) / |EPS_consensus|
```

**What it measures**
How much actual reported EPS deviated from the analyst consensus estimate prior to the announcement. One of the most powerful short-term alpha signals available.

**Interpretation**
- Positive → beat → stock typically jumps on announcement day
- Negative → miss → stock typically falls
- The signal has two components: the announcement-day jump and the post-earnings drift (factor 32)

**Pitfalls**
- Consensus estimates are managed by companies — "beat by a penny" is often engineered
- The surprise is priced in very quickly; only useful if you can act same day or next day
- Requires IBES data; the consensus estimate must be the one from before the announcement

**Data source** — IBES

**Pod columns needed**
```
EPS_actual    (from IBES actuals)
EPS_consensus (from IBES summary, prior to announcement)
earnings_date (event flag)
```

---

## 32. `earnings_revision_30d` — Analyst Estimate Drift

**Equation**
```
(EPS_est_t - EPS_est_{t-30}) / |EPS_est_{t-30}|
```

**What it measures**
How much the consensus EPS estimate has changed over the past 30 days. Analyst revisions are slow — when analysts start revising upward, they tend to continue (revision momentum).

**Interpretation**
- Positive → estimates rising → fundamental momentum → bullish
- Negative → estimates falling → deteriorating outlook → bearish
- One of the strongest and most consistent alpha signals; works because analysts underreact to new information

**Pitfalls**
- Consensus can be moved by a single analyst revision if coverage is sparse — check `analyst_count`
- Most of the signal is in the first revision after an earnings announcement
- Requires point-in-time IBES data (not restated history)

**Data source** — IBES

**Pod columns needed**
```
EPS_consensus_t      (current consensus)
EPS_consensus_t_30   (consensus 30 days ago, from IBES history)
```

---

## 33. `analyst_dispersion` — Disagreement Among Analysts

**Equation**
```
std(individual_EPS_estimates) / |mean(estimates)|
```

**What it measures**
The coefficient of variation of individual analyst EPS estimates. High dispersion means analysts strongly disagree about the company's future earnings.

**Interpretation**
- High → lots of uncertainty → higher risk, often predicts lower returns
- Low → consensus view → market has a clearer picture
- Diether, Malloy, Scherbina (2002): high dispersion predicts underperformance because optimistic investors push prices above fair value

**Pitfalls**
- Requires at least 3–5 analysts for a meaningful standard deviation
- Small-cap stocks often have too few analysts for this to be reliable
- Combine with `analyst_count` — high dispersion with only 2 analysts is not the same as high dispersion with 20

**Data source** — IBES

**Pod columns needed**
```
individual_EPS_estimates  (IBES detail file, not summary)
analyst_count
```

---

---

# Event-Driven Factors

---

## 34. `post_earnings_drift` — PEAD

**Equation**
```
cumulative_return(t+1, t+60)   after earnings announcement date
```

**What it measures**
The cumulative return in the 60 days following an earnings announcement. Post-earnings announcement drift (PEAD) is one of the most studied anomalies: stocks that beat estimates continue drifting up for 1–3 months; stocks that miss continue drifting down.

**Interpretation**
- Positive after a beat → drift is ongoing → momentum
- Negative after a miss → drift is ongoing → avoid or short
- The magnitude of the initial jump predicts the subsequent drift

**Pitfalls**
- The window matters — most drift occurs in the first 30 days, attenuating by day 60
- Transaction costs can eat the signal for small caps
- Requires clean earnings date data — off-by-one errors in the event date destroy the signal

**Data source** — IBES (earnings dates) + Alpaca (price)

**Pod columns needed**
```
earnings_date  (event flag from IBES)
r              (daily log returns, to cumulate post-event)
earnings_surprise  (magnitude of the beat/miss)
```

---

## 35. `insider_buy_sell_ratio` — Insider Purchasing Signal

**Equation**
```
shares_bought_open_market / shares_sold_open_market   over 90 days
```

**What it measures**
The ratio of insider open-market purchases to open-market sales over the trailing 90 days. Insiders buy their own stock for one reason: they think it's cheap. They sell for many reasons (diversification, taxes, liquidity) — so buys are more informative than sells.

**Interpretation**
- High → insiders buying → strong bullish signal, especially if multiple insiders
- Low → insiders selling → weak signal on its own, but corroborates other bearish signals
- Cluster buying (3+ insiders in the same 30-day window) is the strongest version of this signal

**Pitfalls**
- Open-market transactions only — exclude option exercises, gifts, plan sales (10b5-1)
- Low base rate: most stocks have no insider buys in any given quarter
- Requires SEC Form 4 data with transaction type filtering
- Insider selling is almost meaningless as a standalone signal

**Data source** — SEC Form 4 (via EDGAR or a data vendor)

**Pod columns needed**
```
insider_shares_bought  (90-day rolling sum, from Form 4)
insider_shares_sold    (90-day rolling sum, from Form 4)
transaction_type_flag  (open market only)
```

---

---

# Precomputed Pod — Complete Column List

Everything that should be computed once in `build_pod()` before any factor function runs. Grouped by computation pass to respect dependencies.

## Pass 1 — Raw Transforms (no dependencies)

| Column | Expression |
|--------|-----------|
| `r` | `log(close / close.shift(1))` |
| `r_1d` | `close / close.shift(1) - 1` |
| `r_up` | `r.clip(lower=0)` |
| `r_down` | `r.clip(upper=0)` |
| `rsi_gain` | `r_1d.clip(lower=0)` |
| `rsi_loss` | `(-r_1d).clip(lower=0)` |
| `hl` | `high - low` |
| `log_hl` | `log(high / low)` |
| `log_co` | `log(close / open)` |
| `log_hl_sq` | `log_hl ** 2` |
| `log_co_sq` | `log_co ** 2` |
| `abs_r` | `abs(r)` |
| `dv` | `close * volume` |
| `dP` | `close - close.shift(1)` |
| `obv_sign` | `sign(r)` |
| `P_1` | `close.shift(1)` |
| `P_5` | `close.shift(5)` |
| `P_21` | `close.shift(21)` |
| `P_63` | `close.shift(63)` |
| `P_126` | `close.shift(126)` |
| `P_252` | `close.shift(252)` |
| `market_cap` | `close * shares_outstanding` |
| `hc1` | `abs(high - close.shift(1))` |
| `lc1` | `abs(low - close.shift(1))` |

## Pass 2 — Rolling Windows (depend on pass 1)

| Column | Expression |
|--------|-----------|
| `SMA_20` | `close.rolling_mean(20)` |
| `SMA_50` | `close.rolling_mean(50)` |
| `SMA_200` | `close.rolling_mean(200)` |
| `EMA_9` | `close.ewm_mean(span=9)` |
| `EMA_12` | `close.ewm_mean(span=12)` |
| `EMA_20` | `close.ewm_mean(span=20)` |
| `EMA_26` | `close.ewm_mean(span=26)` |
| `std_r_20` | `r.rolling_std(20)` |
| `std_r_60` | `r.rolling_std(60)` |
| `std_r_120` | `r.rolling_std(120)` |
| `std_r_252` | `r.rolling_std(252)` |
| `std_P_20` | `close.rolling_std(20)` |
| `std_r_down_20` | `r_down.rolling_std(20)` |
| `std_r_up_20` | `r_up.rolling_std(20)` |
| `high_14` | `high.rolling_max(14)` |
| `low_14` | `low.rolling_min(14)` |
| `high_60` | `high.rolling_max(60)` |
| `high_252` | `high.rolling_max(252)` |
| `low_252` | `low.rolling_min(252)` |
| `true_range` | `max(hl, hc1, lc1)` |
| `dv_20` | `dv.rolling_mean(20)` |
| `amihud_daily` | `abs_r / dv` |
| `avg_gain_14` | `rsi_gain.ewm_mean(span=14)` |
| `avg_loss_14` | `rsi_loss.ewm_mean(span=14)` |
| `OBV` | `(obv_sign * volume).cum_sum()` |
| `dP_lag1` | `dP.shift(1)` |
| `SMA_20_lag5` | `SMA_20.shift(5)` |
| `SMA_50_lag5` | `SMA_50.shift(5)` |
| `SMA_200_lag5` | `SMA_200.shift(5)` |
| `vol_mean_20` | `volume.rolling_mean(20)` |

## Pass 3 — Derived from Pass 2

| Column | Expression |
|--------|-----------|
| `MACD` | `EMA_12 - EMA_26` |
| `BB_upper` | `SMA_20 + 2 * std_P_20` |
| `BB_lower` | `SMA_20 - 2 * std_P_20` |
| `BB_width` | `(BB_upper - BB_lower) / SMA_20` |
| `ATR_14` | `true_range.rolling_mean(14)` |
| `amihud_20` | `amihud_daily.rolling_mean(20)` |
| `stoch_k` | `100 * (close - low_14) / (high_14 - low_14)` |
| `log_market_cap` | `log(market_cap)` |

## Pass 4 — Derived from Pass 3

| Column | Expression |
|--------|-----------|
| `MACD_signal` | `MACD.ewm_mean(span=9)` |
| `stoch_d` | `stoch_k.rolling_mean(3)` |

## Pass 5 — Derived from Pass 4

| Column | Expression |
|--------|-----------|
| `MACD_hist` | `MACD - MACD_signal` |

---

## Fundamental Data (Separate Join — Not in Price Pod)

These come from Compustat and are joined on `(ticker, date)` after forward-filling quarterly figures to daily frequency.

| Column | Frequency | Source |
|--------|-----------|--------|
| `book_equity` | Quarterly | Compustat `ceq` |
| `EPS_ttm` | Quarterly | Compustat `epspxq` rolling 4q |
| `EBITDA_ttm` | Quarterly | Compustat `oibdpq` rolling 4q |
| `net_debt` | Quarterly | `dlttq + dlcq - cheq` |
| `operating_cashflow` | Annual | Compustat `oancfy` |
| `capex` | Annual | Compustat `capxy` |
| `CFI_ttm` | Annual | Compustat `ivncfy` |
| `net_income_ttm` | Annual | Compustat `niq` rolling 4q |
| `revenue_ttm` | Quarterly | Compustat `saleq` rolling 4q |
| `COGS_ttm` | Quarterly | Compustat `cogsq` rolling 4q |
| `total_assets` | Quarterly | Compustat `atq` |
| `total_debt` | Quarterly | `dlttq + dlcq` |
| `revenue_q` | Quarterly | `saleq` current quarter |
| `revenue_q_4ago` | Quarterly | `saleq` lagged 4 quarters |
| `EPS_q` | Quarterly | `epspxq` current quarter |
| `EPS_q_4ago` | Quarterly | `epspxq` lagged 4 quarters |
| `shares_outstanding` | Daily/Quarterly | Compustat `cshoq` or Alpaca |

## Analyst Data (Separate Join — IBES)

| Column | Frequency | Source |
|--------|-----------|--------|
| `EPS_actual` | Per event | IBES actuals |
| `EPS_consensus` | Monthly | IBES summary |
| `EPS_consensus_t_30` | Monthly | IBES summary (point-in-time) |
| `individual_estimates` | Monthly | IBES detail |
| `analyst_count` | Monthly | IBES summary |
| `earnings_date` | Per event | IBES actuals |

## Event Data (Separate Join)

| Column | Frequency | Source |
|--------|-----------|--------|
| `insider_shares_bought` | Per filing | SEC EDGAR Form 4 |
| `insider_shares_sold` | Per filing | SEC EDGAR Form 4 |
| `transaction_type` | Per filing | Form 4 (`P` = purchase, `S` = sale) |

---

## Important Implementation Notes

**Point-in-time data** — when joining Compustat fundamentals, always use the `datadate` + reporting lag (typically 60–90 days) to avoid look-ahead bias. A Q1 report filed in May should only appear in your factor matrix from May onwards, not from March.

**Forward-fill limit** — forward-fill fundamental data for a maximum of 390 days (roughly 5 quarters). After that, treat as missing rather than stale.

**Winsorisation** — apply before using in a model. Suggested levels: 1st–99th percentile for most factors; 5th–95th for highly skewed ones like Amihud and accruals.

**Cross-sectional normalisation** — z-score each factor within date and optionally within sector/industry before feeding to a model. Raw factor values are not comparable across time.

**Sector neutralisation** — for value and quality factors especially, normalise within GICS sector. A bank with D/E of 10 is not the same as a tech company with D/E of 10.