"""Hidden-pattern miners: weekday, hour, wick, ATR regime, seasonality."""
from __future__ import annotations
import pandas as pd
import numpy as np


def session_volatility(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["hour_utc"] = pd.to_datetime(d["datetime_utc"], utc=True).dt.hour
    d["range"] = d["high"] - d["low"]
    d["ret"] = d["close"].pct_change()
    g = d.groupby("hour_utc").agg(n=("range", "size"), mean_range=("range", "mean"),
                                   mean_abs_ret=("ret", lambda x: x.abs().mean()),
                                   stdev_ret=("ret", "std")).reset_index()
    return g


def weekday_effect(daily: pd.DataFrame) -> pd.DataFrame:
    d = daily.copy()
    d["ret"] = d["close"].pct_change()
    d["weekday"] = pd.to_datetime(d["datetime_utc"], utc=True).dt.day_name()
    g = d.groupby("weekday").agg(n=("ret", "size"), mean_ret=("ret", "mean"),
                                  vol=("ret", "std")).reset_index()
    return g


def wick_edge(df_sig: pd.DataFrame) -> dict:
    d = df_sig.copy()
    # next-bar return conditional on wick size quintile
    d["next_ret"] = d["close"].shift(-1) / d["close"] - 1
    d["wick_q"] = pd.qcut(d["low_wick_ratio"].fillna(0.5), 5, labels=False, duplicates="drop")
    g = d.groupby("wick_q").agg(n=("next_ret", "size"), mean_next_ret=("next_ret", "mean")).reset_index()
    return {"table": g, "corr_wick_nextret": float(d["low_wick_ratio"].corr(d["next_ret"]) or 0)}


def monthly_seasonality(daily: pd.DataFrame) -> pd.DataFrame:
    d = daily.copy()
    d["month"] = pd.to_datetime(d["datetime_utc"], utc=True).dt.month
    d["ret"] = d["close"].pct_change()
    g = d.groupby("month").agg(n=("ret", "size"), mean_ret=("ret", "mean"), vol=("ret", "std")).reset_index()
    return g
