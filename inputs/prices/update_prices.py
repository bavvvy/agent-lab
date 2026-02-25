from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import sys

import pandas as pd
import yfinance as yf
from pandas.tseries.offsets import BDay

SCIENTIST_ROOT = Path(__file__).resolve().parents[2] / "agents" / "scientist"
sys.path.insert(0, str(SCIENTIST_ROOT))

from enforcement.io_guard import assert_not_forbidden_identity_root_file, assert_root_write_allowed

TICKERS = ["SPY", "AGG", "TLT", "TIP", "GLD", "DBC"]
SOURCE = "yfinance"
AUTO_ADJUST = True
START_DATE = pd.Timestamp("2000-01-01")
DATA_DIR = Path(__file__).resolve().parent
REPO_ROOT = DATA_DIR.parents[1]
MARKET_DATA_DIR = REPO_ROOT / "data" / "market"
DATA_PATH = MARKET_DATA_DIR / "prices_master.parquet"
META_PATH = MARKET_DATA_DIR / "prices_master_meta.json"


def _utc_today_date() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(timezone.utc).date())


def _download_prices(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    print(f"[INFO] Downloading {TICKERS} from {start.date()} to {end.date()} (daily, auto_adjust={AUTO_ADJUST})")
    raw = yf.download(
        tickers=TICKERS,
        start=start.strftime("%Y-%m-%d"),
        end=(end + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
        interval="1d",
        auto_adjust=AUTO_ADJUST,
        progress=False,
        group_by="column",
        threads=False,
    )
    if raw.empty:
        raise RuntimeError("No data returned from yfinance")

    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"].copy()
    else:
        close = raw[["Close"]].copy()
        close.columns = [TICKERS[0]]

    missing = [t for t in TICKERS if t not in close.columns]
    if missing:
        raise RuntimeError(f"Missing expected tickers in download: {missing}")

    out = close[TICKERS].copy()
    out.index = pd.to_datetime(out.index).tz_localize(None).normalize()
    out = out[~out.index.duplicated(keep="last")]
    out = out.sort_index()
    return out


def _load_existing() -> pd.DataFrame | None:
    if not DATA_PATH.exists():
        return None
    df = pd.read_parquet(DATA_PATH)
    if "date" in df.columns:
        df = df.set_index("date")
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df = df.sort_index()
    return df


def _save_dataset(df: pd.DataFrame) -> None:
    MARKET_DATA_DIR.mkdir(parents=True, exist_ok=True)
    assert_root_write_allowed(DATA_PATH)
    assert_not_forbidden_identity_root_file(DATA_PATH)
    df_to_save = df.copy()
    df_to_save.index.name = "date"
    df_to_save.to_parquet(DATA_PATH)


def _save_metadata(df: pd.DataFrame) -> None:
    assert_root_write_allowed(META_PATH)
    assert_not_forbidden_identity_root_file(META_PATH)
    meta = {
        "last_update_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "tickers": TICKERS,
        "start_date": str(df.index.min().date()),
        "end_date": str(df.index.max().date()),
        "row_count": int(len(df)),
        "source": SOURCE,
        "auto_adjust_flag": AUTO_ADJUST,
    }
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def main() -> None:
    today = _utc_today_date()
    existing = _load_existing()

    if existing is None or existing.empty:
        print("[INFO] No existing dataset found. Performing full download.")
        merged = _download_prices(START_DATE, today)
    else:
        existing = existing.reindex(columns=TICKERS)
        needs_full_backfill = any(existing[t].isna().all() for t in TICKERS)

        if needs_full_backfill:
            print("[INFO] Detected newly introduced ticker columns with no history. Running full backfill.")
            fetch_start = START_DATE
        else:
            last_date = pd.Timestamp(existing.index.max())
            fetch_start = (last_date - BDay(7)).normalize()
            if fetch_start < START_DATE:
                fetch_start = START_DATE

        new_data = _download_prices(fetch_start, today)

        overlap_idx = existing.index.intersection(new_data.index)
        if len(overlap_idx) > 0:
            left = existing.loc[overlap_idx, TICKERS]
            right = new_data.loc[overlap_idx, TICKERS]
            diff = (left - right).abs()
            changed = (diff > 1e-10).any(axis=1)
            if changed.any():
                changed_dates = overlap_idx[changed]
                print(
                    f"[WARN] Detected differences in overlap window for {len(changed_dates)} date(s). "
                    f"Overwriting from {changed_dates.min().date()} to {changed_dates.max().date()}."
                )

        base = existing.loc[existing.index < fetch_start].copy()
        merged = pd.concat([base, new_data], axis=0)
        merged = merged[~merged.index.duplicated(keep="last")]
        merged = merged.sort_index()

    if merged.empty:
        raise RuntimeError("Merged dataset is empty; aborting")

    _save_dataset(merged)
    _save_metadata(merged)
    print(f"[INFO] Saved dataset: {DATA_PATH}")
    print(f"[INFO] Saved metadata: {META_PATH}")
    print(f"[INFO] Final range: {merged.index.min().date()} -> {merged.index.max().date()} | rows={len(merged)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] {exc}")
        raise
