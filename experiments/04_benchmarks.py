"""04: benchmarks vs Hussein on same data/costs."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd, yaml
from src.strategy import generate_signals
from src.backtest import backtest
from src.metrics import summarise
from src import benchmarks as B

BASE = os.path.dirname(os.path.dirname(__file__))
cfg = yaml.safe_load(open(os.path.join(BASE, "configs/strategy.yaml")))
out = {}
for pair in cfg["pair_universe"]:
    p = os.path.join(BASE, f"data/{pair}_15m.csv")
    if not os.path.exists(p):
        continue
    df = pd.read_csv(p)
    df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], utc=True)
    sig = generate_signals(df, cfg, patient=True)
    hus = summarise(backtest(sig, pair, cfg))
    bh = B.buy_and_hold(df, pair, cfg)
    rnd = summarise(B.random_trades(df, pair, cfg))
    ema = summarise(B.ema25_scalp(df, pair, cfg))
    rsi = summarise(B.rsi_meanrev(df, pair, cfg))
    out[pair] = {"hussein": hus, "buy_hold": {"return_pct": bh["return_pct"], "n_trades": 1},
                 "random": rnd, "ema25": ema, "rsi": rsi}
    print(pair, {k: (v.get("return_pct") if isinstance(v, dict) else v) for k, v in out[pair].items()})
json.dump(out, open(os.path.join(BASE, "results/benchmarks.json"), "w"), indent=2, default=str)
