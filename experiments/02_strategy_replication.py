"""02: replicate Hussein strategy on real 15m per pair + walk-forward."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd, yaml, numpy as np
from src.strategy import generate_signals
from src.backtest import backtest
from src.metrics import summarise

BASE = os.path.dirname(os.path.dirname(__file__))
cfg = yaml.safe_load(open(os.path.join(BASE, "configs/strategy.yaml")))
out = {}
for pair in cfg["pair_universe"]:
    p = os.path.join(BASE, f"data/{pair}_15m.csv")
    if not os.path.exists(p):
        continue
    df = pd.read_csv(p)
    df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], utc=True)
    is_real = bool((df["is_real"] == True).all()) if "is_real" in df.columns else False
    sig = generate_signals(df, cfg, patient=True)
    bt = backtest(sig, pair, cfg)
    m = summarise(bt)
    # walk-forward 4 splits
    n = len(sig)
    splits = 4
    wf = []
    for k in range(splits):
        a = int(n * k / splits)
        b = int(n * (k + 1) / splits)
        seg = sig.iloc[a:b]
        btk = backtest(seg, pair, cfg)
        mk = summarise(btk)
        wf.append({"split": k, "n": mk["n"], "win_rate": mk["win_rate"], "return_pct": mk["return_pct"]})
    out[pair] = {**m, "is_real": is_real, "rows": len(df), "walkforward": wf}
    print(pair, {k: out[pair][k] for k in ["n", "win_rate", "expectancy_R", "return_pct", "max_dd", "is_real"]})
    if bt["trades"] is not None and len(bt["trades"]):
        bt["trades"].to_csv(os.path.join(BASE, f"results/trades_{pair}.csv"), index=False)
json.dump(out, open(os.path.join(BASE, "results/strategy_replication.json"), "w"), indent=2, default=str)
