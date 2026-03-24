import datetime
import pathlib

from loguru import logger
import polars as pl


class DataCleaner:

    _BASEPATH = pathlib.Path(__file__).resolve().parent.parent.parent

    # =====================================================
    # Quality Flags
    # =====================================================

    FLAG_DUPLICATE      = 1 << 0
    FLAG_ZERO_PRICE     = 1 << 1
    FLAG_NEG_VOL        = 1 << 2
    FLAG_INTRADAY_SPIKE = 1 << 3
    FLAG_GAP_SPIKE      = 1 << 4

    # =====================================================
    # Defaults
    # =====================================================

    _DEFAULT_SPIKE_THRESHOLD = 1.5
    _DEFAULT_TS_SIGMA        = 5.0
    _DEFAULT_CS_SIGMA        = 8.0
    _DEFAULT_TS_WINDOW       = 30
    _DEFAULT_TS_MIN_PERIODS  = 5

    _DEFAULT_SCHEMA = {
        "permno": pl.Int32,
        "date": pl.Date,
        "close": pl.Float32,
        "open": pl.Float32,
        "high": pl.Float32,
        "low": pl.Float32,
        "volume": pl.Int64,
        "ret": pl.Float32,
        "retx": pl.Float32,
        "ret_total": pl.Float32,
        "ret_clean": pl.Float32,
        "market_cap": pl.Float64,
        "vwretd": pl.Float32,
        "shrcd": pl.Int32,
        "flags": pl.Int32,
    }

    _CONFIG_PARAMS = {
        "schema":          ("_schema", _DEFAULT_SCHEMA),
        "minimum_price":   ("_min_price", 1.0),
        "minimum_liquid":  ("_min_liquidity", 50_000_000),
        "spike_threshold": ("_spike_threshold", _DEFAULT_SPIKE_THRESHOLD),
        "ts_sigma":        ("_ts_sigma", _DEFAULT_TS_SIGMA),
        "cs_sigma":        ("_cs_sigma", _DEFAULT_CS_SIGMA),
        "ts_window":       ("_ts_window", _DEFAULT_TS_WINDOW),
        "ts_min_periods":  ("_ts_min_periods", _DEFAULT_TS_MIN_PERIODS),
    }

    # =====================================================
    # Init
    # =====================================================

    def __init__(self, config: dict):

        self._logger = logger.bind(class_name=self.__class__.__name__)

        for key, (attr, default) in self._CONFIG_PARAMS.items():
            setattr(self, attr, config.get(key, default))

    # =====================================================
    # Public Pipeline
    # =====================================================

    def run(self, df_dict: dict[str, pl.DataFrame]) -> pl.DataFrame:

        lf = self._merge_dfs(df_dict)
        lf = self._cast_schema(lf)
        lf = self._compute_flags(lf)
        lf = self._clean(lf)
        lf = self._filter_universe(lf)

        return lf.collect()

    # =====================================================
    # Merge
    # =====================================================

    def _merge_dfs(self, df_dict: dict[str, pl.DataFrame]) -> pl.LazyFrame:

        required = ["raw_dsf", "raw_dsenames", "raw_dsi", "delistings"]
        for t in required:
            if t not in df_dict:
                raise ValueError(f"Missing required table: {t}")

        dsf = (
            df_dict["raw_dsf"].lazy()
            .rename({
                "prc": "close",
                "openprc": "open",
                "askhi": "high",
                "bidlo": "low",
                "vol": "volume",
                "shrout": "shares_outstanding_raw",
            })
            .with_columns([
                pl.col("close").abs(),
                pl.col("open").abs(),
                (pl.col("shares_outstanding_raw") * 1000).alias("shares_outstanding"),
            ])
            .drop("shares_outstanding_raw")
        )

        # names join
        dsf = (
            dsf.join(df_dict["raw_dsenames"].lazy(), on="permno", how="left")
            .filter(
                (pl.col("date") >= pl.col("namedt")) &
                (pl.col("nameendt").is_null() | (pl.col("date") <= pl.col("nameendt")))
            )
            .drop(["namedt", "nameendt"])
        )

        # delistings
        delist = df_dict["delistings"].lazy().select([
            "permno", "date",
            pl.col("dlret").alias("delist_ret"),
            pl.col("dlstcd").alias("delist_code"),
        ])

        dsf = dsf.join(delist, on=["permno", "date"], how="left")

        # market index
        dsf = dsf.join(df_dict["raw_dsi"].lazy(), on="date", how="left")

        # derived columns
        dsf = dsf.with_columns([
            ((1 + pl.col("ret").fill_null(0)) *
             (1 + pl.col("delist_ret").fill_null(0)) - 1).alias("ret_total"),

            (pl.col("close") * pl.col("shares_outstanding")).alias("market_cap"),
        ])

        return dsf

    # =====================================================
    # Schema
    # =====================================================

    def _cast_schema(self, lf: pl.LazyFrame) -> pl.LazyFrame:

        existing = set(lf.collect_schema().names())

        return lf.with_columns([
            pl.col(c).cast(t, strict=False)
            for c, t in self._schema.items()
            if c in existing
        ])

    # =====================================================
    # Flags
    # =====================================================

    def _compute_flags(self, lf: pl.LazyFrame) -> pl.LazyFrame:

        thr = self._spike_threshold
        thr_inv = 1 / thr

        prev_close = pl.col("close").shift(1).over("permno")

        flag_expr = pl.sum_horizontal([
            (pl.len().over(["permno", "date"]) > 1).cast(pl.Int32) * self.FLAG_DUPLICATE,
            (pl.col("volume") < 0).cast(pl.Int32) * self.FLAG_NEG_VOL,
            (pl.any_horizontal([pl.col(c) == 0 for c in ["open", "high", "low", "close"]]))
                .cast(pl.Int32) * self.FLAG_ZERO_PRICE,
            (
                (pl.col("close") / pl.col("open") > thr) |
                (pl.col("close") / pl.col("open") < thr_inv)
            ).cast(pl.Int32) * self.FLAG_INTRADAY_SPIKE,
            (
                (pl.col("open") / prev_close > thr) |
                (pl.col("open") / prev_close < thr_inv)
            ).cast(pl.Int32) * self.FLAG_GAP_SPIKE,
        ])

        return lf.with_columns(flags=flag_expr)

    # =====================================================
    # Clean
    # =====================================================

    def _clean(self, lf: pl.LazyFrame) -> pl.LazyFrame:

        # deduplicate
        lf = (
            lf.sort(["permno", "date", "volume"], descending=[False, False, True])
            .group_by(["permno", "date"])
            .agg([
                pl.col("ret_total").first(),
                pl.col("retx").first(),
                pl.col("volume").sum(),
                pl.col("flags").max(),
                pl.col("market_cap").first(),
                pl.col("shrcd").first(),
                pl.col("vwretd").first(),
            ])
            .sort(["permno", "date"])
        )

        # time-series volatility
        lf = lf.with_columns([
            pl.col("ret_total")
            .rolling_std(self._ts_window, min_periods=self._ts_min_periods)
            .over("permno")
            .alias("_ts_std")
        ])

        lf = lf.with_columns([
            pl.when(pl.col("_ts_std").is_not_null())
            .then(pl.col("ret_total").clip(
                -self._ts_sigma * pl.col("_ts_std"),
                 self._ts_sigma * pl.col("_ts_std")))
            .otherwise(pl.col("ret_total"))
            .alias("ret_clean")
        ])

        # cross-sectional
        cs = lf.group_by("date").agg([
            pl.col("ret_clean").mean().alias("_cs_mean"),
            pl.col("ret_clean").std().alias("_cs_std"),
        ])

        lf = lf.join(cs, on="date")

        lf = lf.with_columns([
            ((pl.col("ret_clean") - pl.col("_cs_mean")) / pl.col("_cs_std")).alias("_cs_z")
        ])

        lf = lf.with_columns([
            pl.when(pl.col("_cs_std") > 0)
            .then(
                pl.col("_cs_mean") +
                pl.col("_cs_z").clip(-self._cs_sigma, self._cs_sigma) *
                pl.col("_cs_std")
            )
            .otherwise(pl.col("ret_clean"))
            .alias("ret_clean")
        ])

        return lf.drop(["_ts_std", "_cs_mean", "_cs_std", "_cs_z"])

    # =====================================================
    # Filter
    # =====================================================

    def _filter_universe(self, lf: pl.LazyFrame) -> pl.LazyFrame:

        return lf.filter(
            (pl.col("shrcd").is_in([10, 11])) &
            (pl.col("close") >= self._min_price) &
            (pl.col("market_cap") >= self._min_liquidity) &
            (pl.col("volume") > 0)
        )