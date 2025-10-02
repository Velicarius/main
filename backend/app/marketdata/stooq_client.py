import io
import logging
from datetime import datetime
from typing import Optional, Tuple

import pandas as pd
import requests

STOOQ_EOD_URL = "https://stooq.com/q/d/l/?s={sym}&i=d"
_LOG = logging.getLogger(__name__)


class StooqFetchError(Exception):
    """Exception raised when Stooq API fails"""
    pass

_VALID_SUFFIXES = {".us", ".pl", ".de", ".jp", ".uk", ".fr", ".cn", ".hk", ".in", ".ca"}

def symbol_to_stooq(symbol: str) -> str:
    """
    Normalize a human ticker to Stooq format.
    - Uppercase base symbol.
    - If no market suffix present, default to .US (most common in our app).
    - Preserve existing known suffixes.
    """
    if not symbol:
        raise ValueError("empty symbol")
    s = symbol.strip().lower()
    # if symbol already has a dot suffix, keep it
    if "." in s and any(s.endswith(suf) for suf in _VALID_SUFFIXES):
        base, suf = s.rsplit(".", 1)
        norm = f"{base}.{suf}"
    else:
        norm = f"{s}.us"
    return norm

def _fetch_csv_text(sym_stooq: str, timeout: float = 10.0) -> Tuple[str, int]:
    url = STOOQ_EOD_URL.format(sym=sym_stooq)
    _LOG.info("stooq_request", extra={"url": url, "symbol": sym_stooq})
    
    resp = requests.get(url, timeout=timeout)
    text = resp.text.strip()
    
    # Логируем первые 200 символов ответа
    preview = text[:200] if text else "EMPTY"
    _LOG.info("stooq_response", extra={
        "symbol": sym_stooq, 
        "status": resp.status_code, 
        "preview": preview
    })
    
    return text, resp.status_code

def fetch_eod_dataframe_from_stooq(symbol: str) -> pd.DataFrame:
    """
    Return a DataFrame with at least columns: Date, Open, High, Low, Close, Volume.
    If Stooq returns 'No data' or malformed CSV, return an EMPTY DataFrame (no exception).
    """
    sym_stooq = symbol_to_stooq(symbol)
    text, status = _fetch_csv_text(sym_stooq)
    _LOG.info("stooq_fetch_start", extra={"symbol": symbol, "stooq": sym_stooq, "status": status})

    if not text or text.lower().startswith("no data"):
        _LOG.warning("stooq_no_data", extra={"symbol": symbol, "stooq": sym_stooq})
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])

    try:
        df = pd.read_csv(io.StringIO(text))
        _LOG.info("stooq_dataframe_parsed", extra={
            "symbol": symbol, 
            "stooq": sym_stooq, 
            "columns": list(df.columns),
            "shape": df.shape
        })
    except Exception as e:
        _LOG.error("stooq_csv_parse_error", extra={
            "symbol": symbol, 
            "stooq": sym_stooq, 
            "err": str(e),
            "text_preview": text[:200] if text else "EMPTY"
        })
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])

    # Normalize expected columns
    # Stooq header usually: Date,Open,High,Low,Close,Volume
    cols = {c.lower(): c for c in df.columns}
    required = {"date", "open", "high", "low", "close"}
    if not required.issubset(set(cols.keys())):
        _LOG.error("stooq_missing_columns", extra={"symbol": symbol, "stooq": sym_stooq, "columns": list(df.columns)})
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])

    # Ensure standard casing
    df = df.rename(
        columns={cols["date"]: "Date", cols["open"]: "Open", cols["high"]: "High", cols["low"]: "Low", cols["close"]: "Close"}
    )
    if "volume" in cols:
        df = df.rename(columns={cols["volume"]: "Volume"})
    elif "Volume" not in df.columns:
        df["Volume"] = 0

    # Parse dates
    try:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce", utc=False).dt.date
    except Exception as e:
        _LOG.error("stooq_date_parse_error", extra={"symbol": symbol, "err": str(e)})
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])

    # Drop rows with bad dates
    df = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

    _LOG.info("stooq_fetch_ok", extra={"symbol": symbol, "rows": int(df.shape[0])})
    return df

def fetch_latest_from_stooq(symbol: str) -> Optional[dict]:
    """
    Fetch last available daily bar.
    Returns dict: {date, open, high, low, close, volume} or None.
    """
    df = fetch_eod_dataframe_from_stooq(symbol)
    if df.empty:
        return None
    row = df.iloc[-1]
    return {
        "date": str(row["Date"]),
        "open": float(row["Open"]),
        "high": float(row["High"]),
        "low": float(row["Low"]),
        "close": float(row["Close"]),
        "volume": int(row.get("Volume", 0)),
        "source": "stooq"
    }