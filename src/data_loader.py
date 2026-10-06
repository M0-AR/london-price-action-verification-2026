"""Live public-data loader. No API key. UTC-normalised.

Priority:
 1. Stooq daily CSV (unlimited history, no key) — https://stooq.com/q/d/l/?s=SYM&i=d
 2. Yahoo Finance intraday 15m (last ~60d, no key) via yfinance — for session microstructure
 3. Clearly-labelled synthetic fallback ONLY if offline (never presented as real).

All outputs: data/<PAIR>_<tf>.csv with columns [datetime_utc,open,high,low,close,volume?,source,is_real]
"""
from __future__ import annotations
import io
import os
from datetime import datetime, timezone
import pandas as pd
import requests

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

STOOQ_DAILY = "https://stooq.com/q/d/l/?s={sym}&i=d"
STOOQ_INTRADAY = "https://stooq.com/q/d/l/?s={sym}&i={interval}"  # interval like 15 supported


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def fetch_stooq_daily(stooq_sym: str) -> pd.DataFrame | None:
    try:
        url = STOOQ_DAILY.format(sym=stooq_sym)
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        if "Date" not in r.text[:200]:
            return None
        df = pd.read_csv(io.StringIO(r.text))
        if df.empty or "Close" not in df.columns:
            return None
        df["datetime_utc"] = pd.to_datetime(df["Date"], utc=True)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close"})
        if "Volume" in df.columns:
            df["volume"] = df["Volume"]
        else:
            df["volume"] = 0.0
        df["source"] = "stooq-daily"
        df["is_real"] = True
        return df[["datetime_utc", "open", "high", "low", "close", "volume", "source", "is_real"]]
    except Exception as e:
        print(f"[data] stooq-daily failed for {stooq_sym}: {e}")
        return None


def fetch_stooq_intraday(stooq_sym: str, interval: str = "15") -> pd.DataFrame | None:
    """Stooq intraday CSV (columns vary: Date,Open,High,Low,Close,Volume)."""
    try:
        url = STOOQ_INTRADAY.format(sym=stooq_sym, interval=interval)
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        if "Date" not in r.text[:500]:
            return None
        df = pd.read_csv(io.StringIO(r.text))
        if df.empty:
            return None
        # stooq intraday Date col is like '2024-01-01 00:00:00'
        date_col = "Date" if "Date" in df.columns else df.columns[0]
        df["datetime_utc"] = pd.to_datetime(df[date_col], utc=True)
        colmap = {"Open": "open", "High": "high", "Low": "low", "Close": "close"}
        df = df.rename(columns=colmap)
        if "Volume" in df.columns:
            df["volume"] = df["Volume"]
        elif "volume" not in df.columns:
            df["volume"] = 0.0
        df["source"] = f"stooq-{interval}m"
        df["is_real"] = True
        df = df.dropna(subset=["open", "high", "low", "close"])
        return df[["datetime_utc", "open", "high", "low", "close", "volume", "source", "is_real"]]
    except Exception as e:
        print(f"[data] stooq-intraday failed for {stooq_sym}: {e}")
        return None


def fetch_yahoo_15m(yahoo_sym: str, period: str = "60d") -> pd.DataFrame | None:
    try:
        import yfinance as yf
        df = yf.download(yahoo_sym, period=period, interval="15m", progress=False, auto_adjust=False)
        if df is None or df.empty:
            return None
        # flatten multiindex
        if hasattr(df.columns, "levels"):
            try:
                df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            except Exception:
                pass
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        df["datetime_utc"] = pd.to_datetime(df.index, utc=True)
        for c in ["open", "high", "low", "close"]:
            if c not in df.columns:
                return None
        if "volume" not in df.columns:
            df["volume"] = 0.0
        df["source"] = "yahoo-15m"
        df["is_real"] = True
        out = df[["datetime_utc", "open", "high", "low", "close", "volume", "source", "is_real"]].dropna()
        return out.reset_index(drop=True)
    except Exception as e:
        print(f"[data] yahoo-15m failed for {yahoo_sym}: {e}")
        return None


def fetch_yahoo_daily(yahoo_sym: str, period: str = "5y") -> pd.DataFrame | None:
    try:
        import yfinance as yf
        df = yf.download(yahoo_sym, period=period, interval="1d", progress=False, auto_adjust=False)
        if df is None or df.empty:
            return None
        if hasattr(df.columns, "levels"):
            try:
                df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            except Exception:
                pass
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        df["datetime_utc"] = pd.to_datetime(df.index, utc=True)
        if "volume" not in df.columns:
            df["volume"] = 0.0
        df["source"] = "yahoo-daily"
        df["is_real"] = True
        return df[["datetime_utc", "open", "high", "low", "close", "volume", "source", "is_real"]].dropna().reset_index(drop=True)
    except Exception as e:
        print(f"[data] yahoo-daily failed for {yahoo_sym}: {e}")
        return None


def synthetic_fallback(pair: str, n: int = 2000) -> pd.DataFrame:
    """Clearly fake geometric random walk — ONLY for offline CI smoke tests."""
    import numpy as np
    rng = np.random.default_rng(7)
    idx = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    rets = rng.normal(0, 0.0008, n)
    px = 190.0 if "JPY" in pair else (1.08 if "EURUSD" in pair else 2400.0)
    closes = px * (1 + rets).cumprod()
    df = pd.DataFrame({
        "datetime_utc": idx,
        "open": closes,
        "high": closes * 1.0006,
        "low": closes * 0.9994,
        "close": closes,
        "volume": 0.0,
        "source": "SYNTHETIC-NOT-REAL",
        "is_real": False,
    })
    return df


def load_or_fetch(pair: str, yahoo_sym: str, stooq_sym: str, allow_synthetic: bool = True) -> dict:
    """Returns dict with daily + intraday dataframes + provenance."""
    _ensure_dir()
    daily = fetch_stooq_daily(stooq_sym)
    if daily is None or len(daily) < 100:
        daily = fetch_yahoo_daily(yahoo_sym)
    intra = fetch_stooq_intraday(stooq_sym, "15")
    if intra is None or len(intra) < 500:
        y = fetch_yahoo_15m(yahoo_sym)
        if y is not None and len(y) > 100:
            intra = y if intra is None else pd.concat([intra, y]).drop_duplicates("datetime_utc").sort_values("datetime_utc")
    prov = {"pair": pair, "daily_rows": 0 if daily is None else len(daily),
            "intraday_rows": 0 if intra is None else len(intra),
            "intraday_sources": [] if intra is None else sorted(intra["source"].unique().tolist()),
            "is_real": bool(intra is not None and len(intra) > 100)}
    if daily is not None:
        daily.to_csv(os.path.join(DATA_DIR, f"{pair}_daily.csv"), index=False)
        prov["daily_rows"] = len(daily)
    if intra is not None and len(intra) > 100:
        intra = intra.sort_values("datetime_utc").reset_index(drop=True)
        intra.to_csv(os.path.join(DATA_DIR, f"{pair}_15m.csv"), index=False)
        return {"daily": daily, "intraday": intra, "provenance": prov}
    # never overwrite an existing REAL file with synthetic
    existing = os.path.join(DATA_DIR, f"{pair}_15m.csv")
    if os.path.exists(existing):
        try:
            import pandas as _pd
            old = _pd.read_csv(existing)
            if len(old) > 500 and "SYNTHETIC" not in str(old.get("source", "").astype(str).tolist()[:5]):
                prov["is_real"] = True
                prov["intraday_rows"] = len(old)
                prov["intraday_sources"] = ["cache-kept"]
                return {"daily": daily, "intraday": old, "provenance": prov}
        except Exception:
            pass
    if allow_synthetic:
        synth = synthetic_fallback(pair)
        synth.to_csv(os.path.join(DATA_DIR, f"{pair}_15m.csv"), index=False)
        prov["is_real"] = False
        prov["intraday_sources"] = ["SYNTHETIC-NOT-REAL"]
        return {"daily": daily, "intraday": synth, "provenance": prov}
    return {"daily": daily, "intraday": None, "provenance": prov}
