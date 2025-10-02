from __future__ import annotations
import time
from typing import List, Optional
from fastapi import APIRouter, Query
from urllib.request import urlopen

# Официальные справочники тикеров (обновляются в течение дня)
NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
OTHER_LISTED_URL  = "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"

# Простой in-memory кэш
_CACHE = {"ts": 0.0, "symbols": []}  # symbols: List[str] (UPPERCASE)
TTL_SECONDS = 6 * 3600  # обновляем раз в 6 часов

router = APIRouter(prefix="/symbols/external", tags=["symbols-external"])

def _fetch_txt(url: str, timeout: int = 15) -> str:
    with urlopen(url, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")

def _parse_pipe_table(text: str, cols_expect_min: int = 2) -> List[List[str]]:
    rows: List[List[str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("File Creation Time"):  # хвостовая строка с метаданными
            continue
        parts = line.split("|")
        if len(parts) >= cols_expect_min:
            rows.append(parts)
    return rows

def _load_us_symbols() -> List[str]:
    """
    Возвращает UPPERCASE тикеры США (NASDAQ, NYSE/AMEX и др.), без тестовых,
    без спец-символов. Источник: NasdaqTrader.
    """
    # nasdaqlisted.txt: Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares
    nasdaq = _parse_pipe_table(_fetch_txt(NASDAQ_LISTED_URL))
    # otherlisted.txt: ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol
    other  = _parse_pipe_table(_fetch_txt(OTHER_LISTED_URL))

    syms: set[str] = set()
    # NASDAQ
    for parts in nasdaq[1:]:  # пропускаем заголовок
        try:
            sym, test_issue = parts[0].strip().upper(), parts[3].strip().upper()
            if not sym or test_issue == "Y":
                continue
            if any(c in sym for c in ["^", " ", "/"]):
                continue
            syms.add(sym)
        except Exception:
            continue

    # OTHER (NYSE, AMEX и т.д.)
    for parts in other[1:]:
        try:
            sym, test_issue = parts[0].strip().upper(), parts[6].strip().upper()
            if not sym or test_issue == "Y":
                continue
            if any(c in sym for c in ["^", " ", "/"]):
                continue
            syms.add(sym)
        except Exception:
            continue

    # Немного нормализаций под Stooq: точки (BRK.B) допустимы; оставляем
    return sorted(syms)

def _ensure_cache() -> List[str]:
    now = time.time()
    if now - _CACHE["ts"] > TTL_SECONDS or not _CACHE["symbols"]:
        _CACHE["symbols"] = _load_us_symbols()
        _CACHE["ts"] = now
    return _CACHE["symbols"]

@router.get("/search", response_model=List[str])
def search(q: str = Query(..., min_length=1), limit: int = Query(25, ge=1, le=200)) -> List[str]:
    """
    Поиск по списку тикеров из NasdaqTrader (кэш 6ч).
    Возвращаем UPPERCASE; при использовании со Stooq можно добавлять суффикс .US.
    """
    q_up = q.strip().upper()
    if not q_up:
        return []
    syms = _ensure_cache()
    # фильтруем по подстроке (начало — приоритетно)
    starts = [s for s in syms if s.startswith(q_up)]
    contains = [s for s in syms if q_up in s and s not in starts]
    out = (starts + contains)[:limit]
    return out

@router.get("/popular", response_model=List[str])
def popular(limit: int = Query(20, ge=1, le=200)) -> List[str]:
    """
    Простая "популярность" по эвристике: топ по алфавиту из набора якорей.
    Если нужно умнее — подключим собственную статистику просмотров/частоты в БД.
    """
    anchors = ["SPY","AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","QQQ","BRK.B","V","XOM","UNH","JNJ","PG","JPM","HD","MA","NFLX","AMD"]
    return anchors[:limit]











