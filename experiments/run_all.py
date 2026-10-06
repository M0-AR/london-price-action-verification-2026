"""Run all experiments in order. Fails loudly if real data missing."""
import subprocess, os, sys
BASE = os.path.dirname(__file__)
order = ["00_fetch_live_data.py", "01_session_effect.py", "02_strategy_replication.py",
         "03_ablations.py", "04_benchmarks.py", "05_hidden_patterns.py", "06_walkforward.py"]
for f in order:
    print(f"\n===== {f} =====", flush=True)
    r = subprocess.run([sys.executable, os.path.join(BASE, f)])
    if r.returncode != 0:
        print(f"FAILED: {f}", flush=True)
        sys.exit(r.returncode)
print("\nALL EXPERIMENTS OK. See results/*.json/csv")
