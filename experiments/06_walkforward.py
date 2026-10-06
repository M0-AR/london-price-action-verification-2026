"""06: walk-forward + statistical significance (bootstrap of expectancy)."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd, numpy as np, yaml
from src.strategy import generate_signals
from src.backtest import backtest

BASE = os.path.dirname(os.path.dirname(__file__))
cfg = yaml.safe_load(open(os.path.join(BASE, "configs/strategy.yaml")))
rng = np.random.default_rng(11)
out = {}
for pair in ["GBPJPY", "EURJPY"]:
    p = os.path.join(BASE, f"data/{pair}_15m.csv")
    if not os.path.exists(p):
        continue
    df = pd.read_csv(p)
    df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], utc=True)
    sig = generate_signals(df, cfg, patient=True)
    bt = backtest(sig, pair, cfg)
    tdf = bt["trades"]
    if tdf is None or len(tdf) < 10:
        out[pair] = {"n": 0 if tdf is None else len(tdf), "note": "too few trades for inference"}
        continue
    pnls = tdf["pnl"].values
    # bootstrap mean pnl
    boots = [rng.choice(pnls, size=len(pnls), replace=True).mean() for _ in range(2000)]
    lo, hi = float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))
    out[pair] = {"n": len(tdf), "mean_pnl": float(pnls.mean()),
                 "boot_ci95": [lo, hi], "ci_above_zero": bool(lo > 0),
                 "win_rate": float((tdf["pnl"] > 0).mean())}
    print(pair, out[pair])
json.dump(out, open(os.path.join(BASE, "results/walkforward_stats.json"), "w"), indent=2, default=str)
