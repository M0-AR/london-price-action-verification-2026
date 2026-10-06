"""Smoke tests — must pass without network (synthetic) and with real data if present."""
import os
import pandas as pd

BASE = os.path.dirname(os.path.dirname(__file__))


def test_strategy_imports():
    from src.strategy import generate_signals
    from src.backtest import backtest
    assert callable(generate_signals) and callable(backtest)


def test_backtest_synthetic_runs():
    import yaml
    from src.data_loader import synthetic_fallback
    from src.strategy import generate_signals
    from src.backtest import backtest
    from src.metrics import summarise
    cfg = yaml.safe_load(open(os.path.join(BASE, "configs/strategy.yaml")))
    df = synthetic_fallback("GBPJPY", n=500)
    sig = generate_signals(df, cfg)
    bt = backtest(sig, "GBPJPY", cfg)
    m = summarise(bt)
    assert "n" in m and "win_rate" in m
