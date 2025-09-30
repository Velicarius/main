from __future__ import annotations
import csv
from datetime import datetime
from io import StringIO
from urllib.request import urlopen

class StooqFetchError(Exception):
    pass

def fetch_latest_from_stooq(symbol: str, timeout: int = 10) -> dict | None:
    """
    Возвращает последнюю дневную запись:
      { 'date': date, 'open': float|None, 'high': float|None, 'low': float|None,
        'close': float, 'volume': int|None, 'source': 'stooq' }
    Или None, если данных нет.
    Авто-фоллбек: если данных нет для 'symbol' и в нём нет точки — пробуем 'symbol.us'.
    """
    def _fetch(sym: str) -> dict | None:
        url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
        try:
            with urlopen(url, timeout=timeout) as resp:
                content = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            raise StooqFetchError(f"Failed to fetch {sym} from Stooq: {e}")

        reader = csv.DictReader(StringIO(content))
        rows = list(reader)
        if not rows:
            return None

        last = rows[-1]  # ожидаемые поля: Date,Open,High,Low,Close,Volume
        try:
            d = datetime.strptime(last["Date"], "%Y-%m-%d").date()

            def _f(x: str | None) -> float | None:
                if not x or x == "-":
                    return None
                return float(x)

            def _i(x: str | None) -> int | None:
                if not x or x == "-":
                    return None
                return int(float(x))  # иногда Volume как "0.0"

            close_val = _f(last.get("Close"))
            if close_val is None:
                # Без close запись нам не подходит
                return None

            return {
                "date": d,
                "open": _f(last.get("Open")),
                "high": _f(last.get("High")),
                "low":  _f(last.get("Low")),
                "close": close_val,
                "volume": _i(last.get("Volume")),
                "source": "stooq",
            }
        except Exception as e:
            raise StooqFetchError(f"Malformed CSV for {sym}: {e}")

    sym = symbol.strip().lower()

    # 1) пробуем как есть
    result = _fetch(sym)
    if result is not None:
        return result

    # 2) если нет точки — пробуем .us
    if "." not in sym:
        return _fetch(f"{sym}.us")

    return None





