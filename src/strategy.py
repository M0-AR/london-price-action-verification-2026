"""Hussein strategy formalised (H1-H7 in README).

Long (short mirrored):
 1. London window 06:00-10:00 UTC, Mon-Fri, not UK bank holiday.
 2. HTF bias: H1 close above/below H1 50-EMA (resampled from 15m).
 3. Pullback to support: low == rolling min over support_lookback (20 bars).
 4. Bottom wick: (close-low)/(high-low) >= min_wick_ratio (0.35) and bullish close.
 5. Look-left clean (LTA): no swing high/low obstacle within lta_max_obstacle_atr*ATR to the left over lta_lookback bars.
 6. PATIENCE: signal confirmed ONLY on closed 15m bar (impatient variant enters intra-bar = ablation).
 7. Risk 1%, SL beyond wick +- buffer*ATR, TP = RR*SL. Max 1/day, 5/week, daily loss cap 3%.
"""
from __future__ import annotations
import pandas as pd
import numpy as np


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean().bfill()


def add_features(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    d = df.copy().sort_values("datetime_utc").reset_index(drop=True)
    s = cfg["strategy"]
    d["atr"] = atr(d, s.get("atr_period", 14))
    lb = s.get("support_lookback", 20)
    d["roll_min"] = d["low"].rolling(lb).min()
    d["roll_max"] = d["high"].rolling(lb).max()
    rng = (d["high"] - d["low"]).replace(0, np.nan)
    d["low_wick_ratio"] = (d["close"] - d["low"]) / rng
    d["up_wick_ratio"] = (d["high"] - d["close"]) / rng
    d["body_ratio"] = (d["close"] - d["open"]).abs() / rng
    # H1 bias via resample (map floored hour -> bias, ffill)
    d = d.set_index("datetime_utc")
    d.index = pd.to_datetime(d.index, utc=True)
    h1close = d["close"].resample("1h").last()
    h1ema = h1close.ewm(span=50, adjust=False).mean()
    bias = (h1close > h1ema)
    floored = d.index.floor("h")
    d["htf_bull"] = floored.map(bias)
    d["htf_bull"] = d["htf_bull"].ffill().fillna(True).astype(bool)
    d = d.reset_index()
    # left-obstacle distance (in ATR) for LTA
    lta_lb = s.get("lta_lookback", 5)
    d["left_dist_atr"] = 1.0
    for i in range(len(d)):
        if i < lta_lb + 1 or d["atr"].iloc[i] == 0 or np.isnan(d["atr"].iloc[i]):
            continue
        window = d.iloc[max(0, i - lta_lb):i - 1]
        c = d["close"].iloc[i]
        dist = (window["high"] - window["low"]).abs()
        # obstacle if any bar's range overlaps close within threshold
        overlap = ((window["high"] >= c - 0.1 * d["atr"].iloc[i]) & (window["low"] <= c + 0.1 * d["atr"].iloc[i])).any()
        d.at[i, "left_dist_atr"] = 0.0 if overlap else 1.0
    return d


def is_bank_holiday(ts: pd.Timestamp, holidays: list) -> bool:
    return ts.strftime("%Y-%m-%d") in set(holidays or [])


def generate_signals(df: pd.DataFrame, cfg: dict, patient: bool = True) -> pd.DataFrame:
    """patient=True: use closed-bar values (Hussein rule). patient=False: shift signal 1 bar earlier proxy for intra-candle FOMO."""
    d = add_features(df, cfg)
    s = cfg["strategy"]
    sess = cfg["session"]
    t0, t1 = sess["london_window_utc"]
    h0, h1 = int(t0.split(":")[0]), int(t1.split(":")[0])
    holidays = cfg.get("uk_bank_holidays", [])
    sigs = []
    for i in range(len(d)):
        row = d.iloc[i]
        ts: pd.Timestamp = pd.to_datetime(row["datetime_utc"], utc=True)
        if ts.weekday() not in sess["trade_days"]:
            sigs.append(0)
            continue
        if not (h0 <= ts.hour <= h1):
            sigs.append(0)
            continue
        if is_bank_holiday(ts, holidays):
            sigs.append(0)
            continue
        if row["atr"] == 0 or np.isnan(row["atr"]):
            sigs.append(0)
            continue
        bull_bias = bool(row["htf_bull"])
        at_support = row["low"] <= row["roll_min"] * 1.0005
        at_resist = row["high"] >= row["roll_max"] * 0.9995
        clean_left = row["left_dist_atr"] >= 0.5
        long_setup = bull_bias and at_support and (row["low_wick_ratio"] >= s["min_wick_ratio"]) and (row["close"] > row["open"]) and clean_left
        short_setup = (not bull_bias) and at_resist and (row["up_wick_ratio"] >= s["min_wick_ratio"]) and (row["close"] < row["open"]) and clean_left
        sig = 0
        if long_setup:
            sig = 1
        elif short_setup:
            sig = -1
        sigs.append(sig)
    d["signal"] = sigs
    if not patient:
        # FOMO proxy: act on unconfirmed bar -> shift entries one bar earlier where possible (more noise)
        d["signal"] = d["signal"].shift(-1).fillna(0).astype(int)
    return d
