import datetime
import time
from pathlib import Path
from os import getenv
from typing import Any, Dict, Optional

import polars as pl
import connectorx as cx

from abstract_classes.component import Component
from util.logger import Logger


class WRDS_Client(Component):

    # =====================================================
    # Quality Flags (bitmask)
    # =====================================================

    FLAG_DUPLICATE      = 1 << 0
    FLAG_OHLC_LOGIC     = 1 << 1
    FLAG_ZERO_PRICE     = 1 << 2
    FLAG_NEG_VOL        = 1 << 3
    FLAG_INTRADAY_SPIKE = 1 << 4
    FLAG_GAP_SPIKE      = 1 << 5
    FLAG_FLAT_CANDLE    = 1 << 6
    FLAG_FUTURE_DATE    = 1 << 7
    FLAG_OLD_DATA       = 1 << 8

    # =====================================================
    # Init - FIXED to accept config dict
    # =====================================================

    def __init__(self, config: Dict[str, Any], logger: Optional[Logger] = None) -> None:
        """
        Initialize WRDS_Client with config dict.
        
        Args:
            config: Dict containing WRDS configuration (the 'wrds' section from unified config)
            logger: Optional logger instance
        """
        super().__init__(config=config, config_path=None, logger=logger)

        self._connection = config["connection"]
        self._query      = config["queries"]

        username = getenv("WRDS_USERNAME", "")
        password = getenv("WRDS_PASSWORD", "")
        host     = self._connection["host"]
        port     = self._connection["port"]
        database = self._connection["database"]
        self._url = f"postgresql://{username}:{password}@{host}:{port}/{database}"

        self._path = Path(config["local"]["temp_dir"])
        self._path.mkdir(parents=True, exist_ok=True)

    # =====================================================
    # Internal helpers
    # =====================================================

    def _download_query(self, query: str) -> pl.DataFrame:
        """Execute a SQL query against WRDS with retry/backoff."""
        attempts = self._config["batch"]["max_attempts"]
        backoff  = self._config["batch"]["backoff_seconds"]

        for attempt in range(1, attempts + 1):
            try:
                self._log("info", f"Executing query (attempt {attempt}/{attempts})...")
                df = pl.from_arrow(cx.read_sql(self._url, query, return_type="arrow"))
                self._log("info", f"Query succeeded on attempt {attempt}.")
                return df # type: ignore[return-value]
            except Exception as e:
                self._log("error", f"Query failed on attempt {attempt}: {e}")
                if attempt < attempts:
                    self._log("info", f"Retrying in {backoff}s...")
                    time.sleep(backoff)
                else:
                    self._log("error", "Max attempts reached.")
                    raise

        return pl.DataFrame()  # unreachable — satisfies type checker

    def _cache_query(self, df: pl.DataFrame, filename: Path, hashname: str) -> None:
        """Write DataFrame to parquet and record its hash in config."""
        df.write_parquet(filename)
        row_hash = df.hash_rows().sum()
        self.write_to_config(f"cache.{hashname}.hash", int(row_hash))
        self._log("info", f"Cached query result → {filename}")

    def _compare_query_hash(self, query: str, filename: Path, hashname: str) -> None:
        """
        Refresh cache if the file is older than cache.max_age_hours (default 24).
        Skips the WRDS round-trip entirely if the file is still fresh —
        avoids re-querying on every test run.
        """
        import os
        max_age_hours = self._config.get("cache", {}).get("max_age_hours", 24)
        age_hours = (time.time() - os.path.getmtime(filename)) / 3600

        if age_hours < max_age_hours:
            self._log("info", f"Cache fresh ({age_hours:.1f}h old, max {max_age_hours}h): {filename.name}")
            return

        self._log("info", f"Cache stale ({age_hours:.1f}h old) — re-querying: {filename.name}")
        cached_df   = pl.read_parquet(filename)
        cached_hash = cached_df.hash_rows().sum()

        current_df   = self._download_query(query)
        current_hash = current_df.hash_rows().sum()

        if cached_hash == current_hash:
            self._log("info", f"Cache confirmed up-to-date: {filename.name}")
            # Touch the file so the age resets
            filename.touch()
        else:
            self._log("warning", f"Cache outdated — refreshing: {filename.name}")
            self._cache_query(current_df, filename, hashname)

    def _compute_flags(self, data: pl.LazyFrame) -> pl.LazyFrame:
        """
        Attach a bitmask `flags` column to the LazyFrame.
        Each bit corresponds to a quality rule.
        """
        now        = datetime.datetime.now().date()
        lf         = data
        prev_close = pl.col("close").shift(1).over("permno")

        # Resolve max date — handle str, datetime, or date returned by Polars
        raw_max = lf.select(pl.col("date").max()).collect().item()
        if isinstance(raw_max, str):
            global_max: datetime.date = datetime.date.fromisoformat(raw_max)
        elif isinstance(raw_max, datetime.datetime):
            global_max = raw_max.date()
        else:
            global_max = raw_max  # already datetime.date

        cutoff = pl.lit(global_max - datetime.timedelta(days=365))

        rules = [
            (self.FLAG_DUPLICATE,
             pl.len().over(["permno", "date"]) > 1),

            (self.FLAG_OHLC_LOGIC,
             (pl.col("high") < pl.max_horizontal("open", "close", "low")) |
             (pl.col("low")  > pl.min_horizontal("open", "close", "high"))),

            (self.FLAG_ZERO_PRICE,
             pl.any_horizontal([pl.col(c) == 0 for c in ["open", "high", "low", "close"]])),

            (self.FLAG_NEG_VOL,
             pl.col("volume") < 0),

            (self.FLAG_INTRADAY_SPIKE,
             (pl.col("open") != 0) &
             ((pl.col("close") / pl.col("open") > 1.5) |
              (pl.col("close") / pl.col("open") < 0.66))),

            (self.FLAG_GAP_SPIKE,
             prev_close.is_not_null() &
             (prev_close != 0) &
             ((pl.col("open") / prev_close > 1.5) |
              (prev_close / pl.col("open") > 1.5))),

            (self.FLAG_FLAT_CANDLE,
             (pl.col("open") > 0) &
             ((pl.col("high") - pl.col("low")) / pl.col("open") < 0.001)),

            (self.FLAG_FUTURE_DATE,
             pl.col("date") > pl.lit(now)),

            (self.FLAG_OLD_DATA,
             pl.col("date") < cutoff),
        ]

        flag_expr = pl.sum_horizontal([
            pl.when(cond).then(pl.lit(bit, dtype=pl.Int32)).otherwise(0)
            for bit, cond in rules
        ])

        return lf.with_columns(flags=flag_expr)
    
    def _merge_dfs(self, data: Dict[str, pl.DataFrame]) -> pl.LazyFrame:
        """
        Merge raw CRSP fact tables into a single analysis-ready LazyFrame.

        Join logic:
          dsf        — one row per (permno, date)          — base table
          dsenames   — point-in-time: date BETWEEN namedt AND nameendt
          dsfhdr     — one row per permno (header)         — join on permno only
          delistings — one row per (permno, delist date)   — join on (permno, date)
          dsi        — one row per date (market index)     — join on date only

        Column renames: raw CRSP names → analysis names used by
        _compute_flags() and clean().
        """
        dsf = (
            data["raw_dsf"]
            .rename({
                "prc":     "close",
                "openprc": "open",
                "askhi":   "high",
                "bidlo":   "low",
                "vol":     "volume",
                "shrout":  "shares_outstanding_raw",
            })
            .with_columns([
                pl.col("close").abs(),   # negative prc = bid/ask midpoint
                pl.col("open").abs(),
                (pl.col("shares_outstanding_raw") * 1000).alias("shares_outstanding"),
            ])
        )

        # Point-in-time: date must fall within namedt..nameendt
        dsenames = data["raw_dsenames"]
        dsf_with_names = (
            dsf.join(dsenames, on="permno", how="left")
            .filter(
                (pl.col("date") >= pl.col("namedt")) &
                (pl.col("date") <= pl.col("nameendt"))
            )
            .drop(["namedt", "nameendt"])
        )

        # Header (one row per permno)
        dsfhdr = data["raw_dsfhdr"]
        dsf_with_hdr = dsf_with_names.join(dsfhdr, on="permno", how="left")

        # Delistings (left join on permno + date)
        delistings = data["delistings"]
        dsf_with_delist = dsf_with_hdr.join(
            delistings,
            on=["permno", "date"],
            how="left"
        )

        # Market index (broadcast join on date)
        dsi = data["raw_dsi"]
        merged = dsf_with_delist.join(dsi, on="date", how="left")

        return merged.lazy()

    def _apply_universe_filters(self, lf: pl.LazyFrame) -> pl.LazyFrame:
        """
        Apply universe filters from config:
          - share_codes / exchange_codes (already on dsenames)
          - min_price / min_volume / min_dollar_volume (liquidity)
          - Shumway correction for missing delisting returns
        """
        universe = self._config.get("universe", {})

        # Share/exchange codes already filtered in the query, but double-check
        share_codes    = universe.get("share_codes", [10, 11])
        exchange_codes = universe.get("exchange_codes", [1, 2, 3])
        lf = lf.filter(
            pl.col("shrcd").is_in(share_codes) &
            pl.col("exchange_code").is_in(exchange_codes)
        )

        # Liquidity filters
        liquidity = universe.get("liquidity", {})
        min_price  = liquidity.get("min_price", 0.0)
        min_volume = liquidity.get("min_volume", 0)
        min_dv     = liquidity.get("min_dollar_volume", 0)
        shumway    = universe.get("shumway_correction", -0.30)

        # Liquidity filters — only applied when config value > 0
        if min_price > 0:
            lf = lf.filter(pl.col("close") >= min_price)

        if min_volume > 0:
            lf = lf.filter(pl.col("volume") >= min_volume)

        if min_dv > 0:
            lf = lf.filter(
                (pl.col("close") * pl.col("shares_outstanding")) >= min_dv
            )

        # Shumway correction — impute return for involuntary delistings
        # where CRSP has not provided a delisting return (delist_ret is null)
        lf = lf.with_columns(
            pl.when(
                pl.col("delist_ret").is_null() &
                pl.col("delist_code").is_between(400, 591)
            )
            .then(pl.lit(shumway))
            .otherwise(pl.col("delist_ret"))
            .alias("delist_ret")
        )

        return lf

    # =====================================================
    # Fetch
    # =====================================================

    def fetch(self, params: Dict[str, Any]) -> Optional[Dict[str, pl.DataFrame]]:
        """
        Download (or load from cache) all raw CRSP tables for a date range.

        params:
            start_time (str | datetime.date): inclusive start, e.g. "2020-01-01"
            end_time   (str | datetime.date): inclusive end,   e.g. "2020-12-31"

        Returns a dict keyed by query name, each value a pl.DataFrame,
        or None on invalid params.
        """
        start = params.get("start_time")
        end   = params.get("end_time")

        if start is None or end is None:
            self._log("error", "Missing required params: start_time and end_time")
            return None

        # Normalise strings → date
        if isinstance(start, str):
            start = datetime.datetime.strptime(start, "%Y-%m-%d").date()
        if isinstance(end, str):
            end = datetime.datetime.strptime(end, "%Y-%m-%d").date()

        if not isinstance(start, datetime.date) or not isinstance(end, datetime.date):
            self._log("error", "start_time and end_time must be dates or 'YYYY-MM-DD' strings")
            return None

        if start > end:
            self._log("error", "start_time must be before end_time")
            return None

        start_str = start.strftime("%Y-%m-%d")
        end_str   = end.strftime("%Y-%m-%d")

        query_keys = ["raw_dsf", "raw_dsenames", "raw_dsfhdr", "delistings", "raw_dsi"]
        results: Dict[str, pl.DataFrame] = {}

        # Static tables — no date range in query, cache under a fixed filename
        static_keys = {"raw_dsenames", "raw_dsfhdr"}

        for key in query_keys:
            raw_sql = self._query[key].format(start=start_str, end=end_str)

            if key in static_keys:
                filename = self._path / f"{key}.parquet"
            else:
                filename = self._path / f"{key}_{start_str}_{end_str}.parquet"

            if filename.exists():
                self._log("info", f"Cache hit: {filename.name} — checking freshness...")
                self._compare_query_hash(raw_sql, filename, key)
                results[key] = pl.read_parquet(filename)
            else:
                df = self._download_query(raw_sql)
                self._cache_query(df, filename, key)
                results[key] = df

        return results

    # =====================================================
    # Validate
    # =====================================================

    def validate(self, data: Any) -> bool:
        if not isinstance(data, (pl.DataFrame, pl.LazyFrame)):
            self._log("warning", f"Expected DataFrame or LazyFrame, got {type(data)}")
            return False

        empty = (
            data.limit(1).collect().is_empty()
            if isinstance(data, pl.LazyFrame)
            else data.is_empty()
        )

        if empty:
            self._log("warning", "Empty dataset.")
            return False

        return True

    # =====================================================
    # Compute — quality flags (bitmask)
    # =====================================================

    def compute(self, data: dict[str, pl.DataFrame]) -> pl.LazyFrame:
        """Attach a bitmask `flags` column to the LazyFrame."""
        merged = self._merge_dfs(data)
        flagged = self._compute_flags(merged)
        return flagged

    # =====================================================
    # Clean
    # =====================================================

    def clean(self, data: pl.LazyFrame) -> pl.LazyFrame:
        """
    Three-stage cleaning pipeline:
      1. Deduplicate — aggregate duplicate permno/date rows
      2. Time-series filter — drop outliers beyond 5σ rolling vol
      3. Cross-sectional filter — drop returns beyond 8σ z-score
    """
        lf = data.sort(["permno", "date"])

        # 1. Duplicate aggregation
        lf = (
        lf.group_by(["permno", "date"])
        .agg([
            # Price/volume data (average/max/min/sum as appropriate)
            pl.col("ret").mean(),
            pl.col("retx").mean(),
            pl.col("open").mean(),
            pl.col("high").max(),
            pl.col("low").min(),
            pl.col("close").mean(),
            pl.col("volume").sum(),
            pl.col("flags").max(),
            
            # Bid/ask (for spread calculation)
            pl.col("bid").mean(),
            pl.col("ask").mean(),
            
            # Shares outstanding and adjustment factors
            pl.col("shares_outstanding").first(),
            pl.col("cfacpr").first(),
            pl.col("cfacshr").first(),
            
            # Identifiers (use .first() since they shouldn't change within a day)
            pl.col("ticker").first(),
            pl.col("company_name").first(),
            pl.col("exchange_code").first(),
            pl.col("shrcd").first(),
            pl.col("hshrcd").first(),
            pl.col("hexcd").first(),
            
            # Delisting info (use .first() - only populated on delist date)
            pl.col("delist_ret").first(),
            pl.col("delist_code").first(),
            
            # Market index returns (same for all stocks on a given date)
            pl.col("vwretd").first(),
            pl.col("ewretd").first(),
        ]))

        # 2. Time-series volatility filter (rest stays the same)
        lf = lf.with_columns(
        pl.col("ret")
        .rolling_std(window_size=30)
        .over("permno")
        .alias("ts_std")
        )
        lf = lf.filter(
        pl.col("ts_std").is_null() |
        (pl.col("ret").abs() < 5 * pl.col("ts_std"))
        )

    # 3. Cross-sectional z-score filter
        cs_stats = (
        lf.group_by("date")
        .agg([
            pl.col("ret").mean().alias("cs_mean"),
            pl.col("ret").std().alias("cs_std"),
        ])
        )
        lf = lf.join(cs_stats, on="date")
        lf = lf.with_columns(
        ((pl.col("ret") - pl.col("cs_mean")) /
         pl.when(pl.col("cs_std") > 0)
         .then(pl.col("cs_std"))
         .otherwise(None))
        .alias("cs_z")
        )
        lf = lf.filter(pl.col("cs_z").abs() < 8)

        return lf
    # =====================================================
    # Execute — pass-through (WRDS is read-only)
    # =====================================================

    def execute(self, signal: Dict[str, Any]) -> Any:
        """WRDS_Client is read-only. Writes live in Azure_Client."""
        return signal