"""03: ablations — each Hussein rule knocked out, one at a time (GBPJPY primary)."""
import os, sys, json, copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pandas as pd, yaml
from src.strategy import generate_signals
from src.backtest import backtest
from src.metrics import summarise

BASE = os.path.dirname(os.path.dirname(__file__))
cfg = yaml.safe_load(open(os.path.join(BASE, "configs/strategy.yaml")))
pair = "GBPJPY"
df = pd.read_csv(os.path.join(BASE, f"data/{pair}_15m.csv"))
df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], utc=True)

def run(cfgm, **kw):
    sig = generate_signals(df, cfgm, patient=kw.get("patient", True))
    return summarise(backtest(sig, pair, cfgm, risk=kw.get("risk")))

results = {}
results["baseline_patient_1pct"] = run(cfg)
# A1: no stop-loss (hold 8h, theoretical) -> emulate wide SL via big buffer
c = copy.deepcopy(cfg); c["strategy"]["sl_buffer_atr"] = 10.0; c["strategy"]["rr"] = 0.2
results["A1_no_stop_wideSL"] = run(c)
# A2: impatient (intra-candle FOMO)
results["A2_impatient_FOMO"] = run(cfg, patient=False)
# A3: overtrading (20/week, 5/day)
c = copy.deepcopy(cfg); c["strategy"]["max_trades_per_week"] = 20; c["strategy"]["max_trades_per_day"] = 5
results["A3_overtrading"] = run(c)
# A4: over-risk 5%
results["A4_overrisk_5pct"] = run(cfg, risk=0.05)
# A5: ignore bank-holiday filter
c = copy.deepcopy(cfg); c["uk_bank_holidays"] = []
results["A5_ignore_bankholiday"] = run(c)
# A6: ignore LTA (allow crowded left)
c = copy.deepcopy(cfg); c["strategy"]["lta_lookback"] = 0
# emulate by patching signal: accept all (generate then OR) — simplest: min_wick 0
c["strategy"]["min_wick_ratio"] = 0.0
results["A6_no_wick_no_LTA"] = run(c)

json.dump(results, open(os.path.join(BASE, "results/ablations.json"), "w"), indent=2, default=str)
print(json.dumps(results, indent=2, default=str))
