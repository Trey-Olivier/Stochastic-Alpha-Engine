import datetime
import pathlib

import polars as pl


class DataCleaner:

    _BASEPATH = pathlib.Path(__file__).resolve().parent.parent.parent

    # =====================================================
    # Quality Flags (bitmask)
    # =====================================================

    FLAG_DUPLICATE      = 1 << 0   # multiple rows for same (permno, date)
    FLAG_OHLC_LOGIC     = 1 << 1   # high < max(o,c,l) or low > min(o,c,h)
    FLAG_ZERO_PRICE     = 1 << 2   # any price field is exactly zero
    FLAG_NEG_VOL        = 1 << 3   # volume < 0
    FLAG_INTRADAY_SPIKE = 1 << 4   # close/open outside [0.66, 1.5]
    FLAG_GAP_SPIKE      = 1 << 5   # open vs prev_close outside [0.67, 1.5]
    FLAG_FLAT_CANDLE    = 1 << 6   # (high - low) / open < 0.001
    FLAG_FUTURE_DATE    = 1 << 7   # date after today
    FLAG_OLD_DATA       = 1 << 8   # date before 1980-01-01

    # =====================================================
    # Defaults (overridden by config)
    # =====================================================

    _DEFAULT_SPIKE_THRESHOLD = 1.5    # ratio threshold for intraday / gap spikes
    _DEFAULT_TS_SIGMA        = 5.0    # time-series rolling-vol filter (σ)
    _DEFAULT_CS_SIGMA        = 8.0    # cross-sectional z-score filter (σ)
    _DEFAULT_TS_WINDOW       = 30     # rolling window for ts_std
    _DEFAULT_TS_MIN_PERIODS  = 5      # min obs before ts filter activates
    _OLD_DATA_CUTOFF         = datetime.date(1980, 1, 1)

    def __init__(self, config: dict):
        self.config = config
        self._spike_threshold = config.get("spike_threshold", self._DEFAULT_SPIKE_THRESHOLD)
        self._ts_sigma        = config.get("ts_sigma",        self._DEFAULT_TS_SIGMA)
        self._cs_sigma        = config.get("cs_sigma",        self._DEFAULT_CS_SIGMA)
        self._ts_window       = config.get("ts_window",       self._DEFAULT_TS_WINDOW)
        self._ts_min_periods  = config.get("ts_min_periods",  self._DEFAULT_TS_MIN_PERIODS)

    # =====================================================
    # Public pipeline entry point
    # =====================================================

    def run(self, df_dict: dict[str, pl.DataFrame]) -> pl.DataFrame:
        """Full pipeline: merge → flag → clean."""
        merged  = self._merge_dfs(df_dict)
        typed   = self._cast_schema(merged)
        flagged = self.compute_flags(typed)
        cleaned = self.clean(flagged)

        return cleaned.collect()  

    # =====================================================
    # Step 1 — Merge raw tables
    # =====================================================

    def _merge_dfs(self, df_dict: dict[str, pl.DataFrame]) -> pl.LazyFrame:

        dsf = (
            df_dict["raw_dsf"].lazy()
            .rename({
                "prc":     "close",
                "openprc": "open",
                "askhi":   "high",
                "bidlo":   "low",
                "vol":     "volume",
                "shrout":  "shares_outstanding_raw",})
            .with_columns([
                pl.col("close").abs(),
                pl.col("open").abs(),
                (pl.col("shares_outstanding_raw") * 1000).alias("shares_outstanding"),])
            .drop("shares_outstanding_raw"))

        # --- Names (point-in-time) ---
        dsf = (
            dsf.join(df_dict["raw_dsenames"].lazy(), on="permno", how="left")
            .filter(
                (pl.col("date") >= pl.col("namedt")) &
                (pl.col("nameendt").is_null() | (pl.col("date") <= pl.col("nameendt"))))
            .drop(["namedt", "nameendt"]))

        # --- Header ---
        dsf = dsf.join(df_dict["raw_dsfhdr"].lazy(), on="permno", how="left")

        # --- Delistings ---
        delistings = (
            df_dict["delistings"].lazy()
            .select([
                "permno",
                "date",
                pl.col("dlret").alias("delist_ret"),
                pl.col("dlstcd").alias("delist_code"),]))

        dsf = dsf.join(delistings, on=["permno", "date"], how="left")

        # --- Market index ---
        dsf = dsf.join(df_dict["raw_dsi"].lazy(), on="date", how="left")

        dsf = dsf.with_columns([
            # --- Adjusted prices ---
            (pl.col("close") / pl.col("cfacpr")).alias("adj_close"),
            (pl.col("open")  / pl.col("cfacpr")).alias("adj_open"),
            (pl.col("high")  / pl.col("cfacpr")).alias("adj_high"),
            (pl.col("low")   / pl.col("cfacpr")).alias("adj_low"),

            # --- Total return (includes delisting) ---
            
                ((1 + pl.col("ret").fill_null(0)) *
                (1 + pl.col("delist_ret").fill_null(0)) - 1
            ).alias("ret_total"),

            # --- Market cap ---
            (pl.col("close").abs() * pl.col("shares_outstanding"))
            .alias("market_cap"),

            # --- Excess return ---
            (pl.col("ret").fill_null(0) - pl.col("vwretd").fill_null(0))
            .alias("excess_ret"),])

        return dsf

    # =====================================================
    # Step 2 — Cast to Types
    # =====================================================

    def _cast_schema(self, lf: pl.LazyFrame) -> pl.LazyFrame:
        """Cast all known columns to canonical types. Unknown columns pass through."""
        existing = set(lf.collect_schema().names())
        return lf.with_columns(
            [pl.col(col).cast(dtype, strict=False) 
            for col, dtype in self._SCHEMA.items() 
            if col in existing])


    # =====================================================
    # Step 3 — Quality flags
    # =====================================================

    def compute_flags(self, lf: pl.LazyFrame) -> pl.LazyFrame:
        """
        Attach an integer bitmask column `flags` to every row.
        Each bit corresponds to a FLAG_* constant.  Multiple issues
        on the same row accumulate by OR (implemented as integer sum
        since bits are non-overlapping).
        """
        thr  = self._spike_threshold
        thr_inv = 1.0 / thr          # lower bound (≈ 0.67 for threshold=1.5)

        prev_close = pl.col("close").shift(1).over("permno")

        today    = pl.lit(datetime.date.today())
        old_date = pl.lit(self._OLD_DATA_CUTOFF)

        rules: list[tuple[int, pl.Expr]] = [
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
             pl.col("open").is_not_null() &
             (pl.col("open") != 0) &
             (
                 (pl.col("close") / pl.col("open") > thr) |
                 (pl.col("close") / pl.col("open") < thr_inv)
             )),

            (self.FLAG_GAP_SPIKE,
             prev_close.is_not_null() &
             (prev_close != 0) &
             (
                 (pl.col("open") / prev_close > thr) |
                 (prev_close / pl.col("open") > thr)
             )),

            (self.FLAG_FLAT_CANDLE,
             pl.col("open").is_not_null() &
             (pl.col("open") > 0) &
             ((pl.col("high") - pl.col("low")) / pl.col("open") < 0.001)),

            (self.FLAG_FUTURE_DATE,
             pl.col("date") > today),

            (self.FLAG_OLD_DATA,
             pl.col("date") < old_date),
        ]

        flag_expr = pl.sum_horizontal([
            pl.when(cond).then(pl.lit(bit, dtype=pl.Int32)).otherwise(pl.lit(0, dtype=pl.Int32))
            for bit, cond in rules
        ])

        return lf.with_columns(flags=flag_expr)

    # =====================================================
    # Step 4 — Clean
    # =====================================================

    def clean(self, data: pl.LazyFrame) -> pl.LazyFrame:

        # --- 1. Deduplicate (FIXED: no averaging returns) ---
        lf = (
            data.group_by(["permno", "date"])
            .agg([
                pl.col("ret_total").first(),
                pl.col("retx").first(),

                pl.col("adj_open").mean(),
                pl.col("adj_high").max(),
                pl.col("adj_low").min(),
                pl.col("adj_close").mean(),

                pl.col("volume").sum(),
                pl.col("flags").max(),

                pl.col("shares_outstanding").first(),
                pl.col("market_cap").first(),

                pl.col("ticker").first(),
                pl.col("company_name").first(),
                pl.col("exchange_code").first(),
                pl.col("shrcd").first(),

                pl.col("delist_ret").first(),
                pl.col("delist_code").first(),

                pl.col("vwretd").first(),
                pl.col("ewretd").first(),]))

        # --- 2. Sort ---
        lf = lf.sort(["permno", "date"])

        # --- 3. Time-series volatility ---
        lf = lf.with_columns(
            pl.col("ret_total")
            .rolling_std(window_size=self._ts_window, min_periods=self._ts_min_periods)
            .over("permno")
            .alias("_ts_std"))

    
        lf = lf.with_columns([
            pl.when(pl.col("_ts_std").is_not_null())
            .then(
                pl.col("ret_total").clip(
                    -self._ts_sigma * pl.col("_ts_std"),
                     self._ts_sigma * pl.col("_ts_std")))
            .otherwise(pl.col("ret_total"))
            .alias("ret_clean")])

        # --- 4. Cross-sectional stats ---
        cs_stats = (
            lf.group_by("date")
            .agg([
                pl.col("ret_clean").mean().alias("_cs_mean"),
                pl.col("ret_clean").std().alias("_cs_std"),]))

        lf = lf.join(cs_stats, on="date")

        lf = lf.with_columns([
            ((pl.col("ret_clean") - pl.col("_cs_mean")) /
            pl.when(pl.col("_cs_std") > 0)
            .then(pl.col("_cs_std"))
            .otherwise(None)
            ).alias("_cs_z")])

    
        lf = lf.with_columns([
            pl.col("_cs_z").clip(-self._cs_sigma, self._cs_sigma)])

        return lf.drop(["_ts_std", "_cs_mean", "_cs_std", "_cs_z"])