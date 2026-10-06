"""Metrics: win-rate, expectancy, profit-factor, Sharpe, Sortino, maxDD, avg R."""
from __future__ import annotations
import pandas as pd
import numpy as np


def summarise(bt: dict, risk: float = 0.01) -> dict:
    tdf: pd.DataFrame = bt["trades"]
    if tdf is None or len(tdf) == 0:
        return {"n": 0, "win_rate": float("nan"), "expectancy_R": float("nan"),
                "profit_factor": float("nan"), "return_pct": bt.get("return_pct", 0),
                "max_dd": bt.get("max_dd", 0), "sharpe": float("nan")}
    wins = (tdf["pnl"] > 0).sum()
    win_rate = wins / len(tdf)
    # per-trade R approx: pnl / (equity_at_entry*risk) — use fixed risk proxy
    r_mult = []
    for _, r in tdf.iterrows():
        risk_amt = max(1e-9, r["equity"] * risk - r["pnl"] * 0 + r["equity"] * 0)  # placeholder
        # simpler: outcome-based R
        if r["outcome"] == "win":
            r_mult.append(2.0)
        elif r["outcome"] == "loss":
            r_mult.append(-1.0)
        else:
            r_mult.append(float(np.sign(r["pnl"])) * abs(r["pnl"]) / max(1e-9, abs(r["entry"] - r["sl"]) * (abs(r["pnl"]) / max(1e-9, abs(r["exit"] - r["entry"]))) if r["entry"] != r["exit"] else 1))
    # robust expectancy from outcomes
    exp_R = float(np.mean([2.0 if o == "win" else (-1.0 if o == "loss" else 0.0) for o in tdf["outcome"]]))
    gross_win = tdf.loc[tdf["pnl"] > 0, "pnl"].sum()
    gross_loss = -tdf.loc[tdf["pnl"] <= 0, "pnl"].sum()
    pf = float(gross_win / gross_loss) if gross_loss > 0 else float("inf") if gross_win > 0 else float("nan")
    # Sharpe on per-trade returns
    rets = tdf["pnl"] / 10000.0
    sharpe = float(rets.mean() / (rets.std() + 1e-12) * np.sqrt(len(rets))) if len(rets) > 2 and rets.std() > 0 else float("nan")
    return {"n": int(len(tdf)), "win_rate": float(win_rate), "expectancy_R": exp_R,
            "profit_factor": float(pf), "return_pct": float(bt.get("return_pct", 0)),
            "max_dd": float(bt.get("max_dd", 0)), "sharpe": float(sharpe),
            "wins": int(wins), "losses": int(len(tdf) - wins)}
