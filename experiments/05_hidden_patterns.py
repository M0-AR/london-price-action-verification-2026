"""05: hidden patterns — weekday/hour/wick/seasonality (real data only flagged)."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd, yaml
from src.hidden_patterns import weekday_effect, wick_edge, monthly_seasonality, session_volatility
from src.strategy import generate_signals

BASE = os.path.dirname(os.path.dirname(__file__))
cfg = yaml.safe_load(open(os.path.join(BASE, "configs/strategy.yaml")))
summary = {}
for pair in cfg["pair_universe"]:
    p15 = os.path.join(BASE, f"data/{pair}_15m.csv")
    pdly = os.path.join(BASE, f"data/{pair}_daily.csv")
    if not os.path.exists(p15):
        continue
    df = pd.read_csv(p15)
    df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], utc=True)
    sig = generate_signals(df, cfg, patient=True)
    we = wick_edge(sig)
    we["table"].to_csv(os.path.join(BASE, f"results/wick_{pair}.csv"), index=False)
    sv = session_volatility(df)
    best_hour = int(sv.sort_values("mean_range", ascending=False).iloc[0]["hour_utc"])
    entry = {"best_vol_hour_utc": best_hour, "wick_corr": we["corr_wick_nextret"]}
    if os.path.exists(pdly):
        dly = pd.read_csv(pdly)
        weekday_effect(dly).to_csv(os.path.join(BASE, f"results/weekday_{pair}.csv"), index=False)
        monthly_seasonality(dly).to_csv(os.path.join(BASE, f"results/monthly_{pair}.csv"), index=False)
        wd = weekday_effect(dly)
        mo = monthly_seasonality(dly)
        entry["best_weekday_by_ret"] = str(wd.sort_values("mean_ret", ascending=False).iloc[0]["weekday"]) if len(wd) else "n/a"
        entry["best_month_by_ret"] = int(mo.sort_values("mean_ret", ascending=False).iloc[0]["month"]) if len(mo) else -1
    summary[pair] = entry
    print(pair, entry)
json.dump(summary, open(os.path.join(BASE, "results/hidden_patterns.json"), "w"), indent=2, default=str)
