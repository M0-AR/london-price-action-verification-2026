"""Benchmarks: buy-and-hold, random, EMA25 scalping, RSI — same cost model."""
from __future__ import annotations
import pandas as pd
import numpy as np
from .backtest import spread_price


def _simulate(df: pd.DataFrame, signals: pd.Series, pair: str, cfg: dict, tag: str) -> dict:
    from .backtest import backtest
    from .strategy import atr as _atr
    d = df.copy()
    if "atr" not in d.columns:
        d["atr"] = _atr(d, cfg["strategy"].get("atr_period", 14))
    d["signal"] = signals.values
    # reuse risk engine but force signals; for buy-hold we handle separately
    return backtest(d, pair, cfg)


def buy_and_hold(df: pd.DataFrame, pair: str, cfg: dict) -> dict:
    if df is None or len(df) < 2:
        return {"equity": 10000, "return_pct": 0, "n_trades": 1, "max_dd": 0}
    spread = spread_price(pair, cfg)
    entry = float(df["close"].iloc[0]) + spread / 2
    exitp = float(df["close"].iloc[-1]) - spread / 2
    # size so 1% risk on 1 ATR? approximate: full notional 10k base units scaled
    ret = (exitp - entry) / entry
    equity = 10000 * (1 + ret)
    return {"equity": equity, "return_pct": ret * 100, "n_trades": 1, "max_dd": float("nan")}


def random_trades(df: pd.DataFrame, pair: str, cfg: dict, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    # same frequency as strategy would trade in London window: ~ same count
    sig = pd.Series(rng.choice([0, 0, 0, 0, 1, -1], size=len(df)), index=df.index)
    d = df.copy()
    # restrict to London window like strategy
    hours = pd.to_datetime(d["datetime_utc"], utc=True).dt.hour
    sig = sig.where((hours >= 6) & (hours <= 10), 0)
    return _simulate(d, sig, pair, cfg, "random")


def ema25_scalp(df: pd.DataFrame, pair: str, cfg: dict) -> dict:
    """EasyTradeWeb GBPJPY 20-pip scalping proxy: 25-EMA trend + 20-pip TP / 10-pip SL."""
    from .strategy import atr as _atr
    d = df.copy()
    if "atr" not in d.columns:
        d["atr"] = _atr(d, cfg["strategy"].get("atr_period", 14))
    ema = d["close"].ewm(span=25, adjust=False).mean()
    sig = []
    for i in range(len(d)):
        if i < 26:
            sig.append(0)
            continue
        slope = ema.iloc[i] - ema.iloc[i - 3]
        if d["close"].iloc[i] > ema.iloc[i] and slope > 0 and d["close"].iloc[i - 1] <= ema.iloc[i - 1]:
            sig.append(1)
        elif d["close"].iloc[i] < ema.iloc[i] and slope < 0 and d["close"].iloc[i - 1] >= ema.iloc[i - 1]:
            sig.append(-1)
        else:
            sig.append(0)
    return _simulate(d, pd.Series(sig, index=d.index), pair, cfg, "ema25")


def rsi_meanrev(df: pd.DataFrame, pair: str, cfg: dict, period: int = 14) -> dict:
    from .strategy import atr as _atr
    d = df.copy()
    if "atr" not in d.columns:
        d["atr"] = _atr(d, cfg["strategy"].get("atr_period", 14))
    delta = d["close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / (loss + 1e-12)
    rsi = 100 - 100 / (1 + rs)
    sig = ((rsi < 30).astype(int) - (rsi > 70).astype(int)).fillna(0).astype(int)
    hours = pd.to_datetime(d["datetime_utc"], utc=True).dt.hour
    sig = sig.where((hours >= 6) & (hours <= 10), 0)
    return _simulate(d, sig, pair, cfg, "rsi")
