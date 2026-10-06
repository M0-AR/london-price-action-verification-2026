"""01: session effect — is London 06-10 UTC special? Real 15m ranges by hour."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd, yaml
from src.hidden_patterns import session_volatility

BASE = os.path.dirname(os.path.dirname(__file__))
cfg = yaml.safe_load(open(os.path.join(BASE, "configs/strategy.yaml")))
res = {}
for pair in cfg["pair_universe"]:
    p = os.path.join(BASE, f"data/{pair}_15m.csv")
    if not os.path.exists(p):
        continue
    df = pd.read_csv(p)
    if df.get("is_real", True) is False or (df["source"].astype(str).str.contains("SYNTHETIC").any()):
        real = df[~df["source"].astype(str).str.contains("SYNTHETIC")]
        if len(real) > 200:
            df = real
    t = session_volatility(df)
    t.to_csv(os.path.join(BASE, f"results/session_vol_{pair}.csv"), index=False)
    london = t[t["hour_utc"].between(6, 10)]["mean_range"].mean()
    asia = t[t["hour_utc"].between(0, 5)]["mean_range"].mean()
    ny = t[t["hour_utc"].between(12, 16)]["mean_range"].mean()
    res[pair] = {"london_mean_range": float(london or 0), "asia_mean_range": float(asia or 0),
                 "ny_mean_range": float(ny or 0),
                 "london_vs_asia": float((london or 0) / (asia or 1e-9)),
                 "rows": len(df), "is_real": bool((df["is_real"] == True).all()) if "is_real" in df else True}
    print(pair, res[pair])
json.dump(res, open(os.path.join(BASE, "results/session_effect.json"), "w"), indent=2)
