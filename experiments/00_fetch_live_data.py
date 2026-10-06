"""00: fetch live public data for all pairs. Writes data/*.csv + results/provenance.json"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import yaml
from src.data_loader import load_or_fetch

BASE = os.path.dirname(os.path.dirname(__file__))
cfg = yaml.safe_load(open(os.path.join(BASE, "configs", "strategy.yaml")))
os.makedirs(os.path.join(BASE, "results"), exist_ok=True)
prov_all = {}
for pair in cfg["pair_universe"]:
    ysym = cfg["yahoo_symbols"][pair]
    ssym = cfg["stooq_symbols"][pair]
    print(f"[00] fetching {pair} yahoo={ysym} stooq={ssym} ...", flush=True)
    out = load_or_fetch(pair, ysym, ssym, allow_synthetic=True)
    prov_all[pair] = out["provenance"]
    print(f"  -> {out['provenance']}", flush=True)
json.dump(prov_all, open(os.path.join(BASE, "results", "provenance.json"), "w"), indent=2)
print("[00] done. provenance:", prov_all)
