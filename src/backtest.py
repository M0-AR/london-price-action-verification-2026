"""Event-driven backtest: 1% risk, spread, 2R, 1/day 5/week, 3% daily cap."""
from __future__ import annotations
import pandas as pd
import numpy as np


def pip_size(pair: str) -> float:
    if "JPY" in pair:
        return 0.01
    if "XAU" in pair or "GOLD" in pair:
        return 0.1
    return 0.0001


def spread_price(pair: str, cfg: dict) -> float:
    s = cfg["strategy"]
    key = f"spread_pips_{pair}"
    pips = float(s.get(key, 2.0))
    return pips * pip_size(pair)


def backtest(df_sig: pd.DataFrame, pair: str, cfg: dict, risk: float | None = None) -> dict:
    s = cfg["strategy"]
    risk = s["risk_per_trade"] if risk is None else risk
    spread = spread_price(pair, cfg)
    rr = s["rr"]
    buf = s["sl_buffer_atr"]
    equity = 10000.0
    peak = equity
    max_dd = 0.0
    trades = []
    week_count: dict = {}
    day_count: dict = {}
    day_pnl: dict = {}
    equity_curve = []
    for i in range(len(df_sig)):
        row = df_sig.iloc[i]
        ts = pd.to_datetime(row["datetime_utc"], utc=True)
        equity_curve.append((ts, equity))
        sig = int(row.get("signal", 0))
        if sig == 0:
            continue
        day = ts.strftime("%Y-%m-%d")
        week = f"{ts.isocalendar().year}-W{ts.isocalendar().week}"
        if day_count.get(day, 0) >= s["max_trades_per_day"]:
            continue
        if week_count.get(week, 0) >= s["max_trades_per_week"]:
            continue
        if day_pnl.get(day, 0) <= -s["daily_loss_cap"] * 10000:
            continue
        entry = float(row["close"]) + (spread / 2 if sig == 1 else -spread / 2)
        atr = float(row["atr"])
        if sig == 1:
            sl = float(row["low"]) - buf * atr - spread / 2
        else:
            sl = float(row["high"]) + buf * atr + spread / 2
        sl_dist = abs(entry - sl)
        if sl_dist <= 0:
            continue
        tp = entry + rr * sl_dist if sig == 1 else entry - rr * sl_dist
        # forward scan next 32 bars for SL/TP hit (8h on 15m)
        exit_px, outcome = None, "timeout"
        fwd = df_sig.iloc[i + 1:i + 33]
        for _, b in fwd.iterrows():
            if sig == 1:
                if b["low"] <= sl:
                    exit_px, outcome = sl, "loss"
                    break
                if b["high"] >= tp:
                    exit_px, outcome = tp, "win"
                    break
            else:
                if b["high"] >= sl:
                    exit_px, outcome = sl, "loss"
                    break
                if b["low"] <= tp:
                    exit_px, outcome = tp, "win"
                    break
        if exit_px is None:
            exit_px = float(fwd["close"].iloc[-1]) if len(fwd) else entry
            outcome = "timeout"
        # position size: risk% / sl_dist
        risk_amt = equity * risk
        size = risk_amt / sl_dist  # units of base
        pnl = (exit_px - entry) * size if sig == 1 else (entry - exit_px) * size
        # spread already in entry/sl; charge extra commission proxy 0
        equity += pnl
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak if peak else 0)
        trades.append({"time": ts, "side": sig, "entry": entry, "sl": sl, "tp": tp,
                       "exit": exit_px, "pnl": pnl, "equity": equity, "outcome": outcome})
        day_count[day] = day_count.get(day, 0) + 1
        week_count[week] = week_count.get(week, 0) + 1
        day_pnl[day] = day_pnl.get(day, 0) + pnl
    tdf = pd.DataFrame(trades)
    return {"equity": equity, "return_pct": (equity / 10000 - 1) * 100,
            "n_trades": len(tdf), "max_dd": max_dd,
            "trades": tdf, "equity_curve": pd.DataFrame(equity_curve, columns=["time", "equity"])}
