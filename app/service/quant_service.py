"""Quant-value fetcher — the piece neither the ML package nor the backend owned.

`pipeline.evaluator.evaluate` *consumes* `quant_results` but never computes them.
This module fills that gap: pull live fundamentals (Finnhub primary, yfinance
fallback) and compare them against a thesis's `QuantCondition` rows, producing
the exact three-valued shape
the evaluator aligns 1:1 with `thesis["quant_conditions"]`:

    {"value": float | None, "passes": bool | None}   # passes is None == couldn't evaluate

`fetch_metrics` (network) and `evaluate_conditions` (pure) are split so the
comparison logic is testable without hitting yfinance.
"""
import time

import requests

from app.config import settings
from app.core.logger import logger

FINNHUB_BASE = "https://finnhub.io/api/v1"

# --- rate-limit backoff + cache tunables ---
_RATE_LIMIT_MARKERS = ("too many requests", "rate limit", "rate-limit", "429")
_MAX_RETRIES = 2               # retries AFTER the first attempt (3 tries total)
_BACKOFF_BASE_SECONDS = 1.0    # 1s, 2s exponential; only on rate-limit errors

# Per-ticker TTL cache: ticker -> (expires_at_monotonic, values). A module-level
# dict is fine — the scheduler runs on a single event loop. Within one cycle this
# also gives ticker dedup for free: the first thesis on a ticker fetches, the rest
# hit the cache.
_cache: dict[str, tuple[float, dict[str, float | None]]] = {}

# Backend `QuantCondition.metric` (snake_case) -> yfinance `.info` key.
# yfinance is the keyless fallback; Finnhub (below) is primary when a key is set.
METRIC_MAP: dict[str, str] = {
    "forward_pe": "forwardPE",
    "trailing_pe": "trailingPE",
    "price_to_book": "priceToBook",
    "price_to_sales": "priceToSalesTrailing12Months",
    "peg_ratio": "trailingPegRatio",
    "market_cap": "marketCap",
    "dividend_yield": "dividendYield",
    "beta": "beta",
    "current_price": "currentPrice",
    "eps": "trailingEps",
    "profit_margin": "profitMargins",
    "revenue_growth": "revenueGrowth",
    "debt_to_equity": "debtToEquity",
}

# Backend metric -> Finnhub /stock/metric field. Finnhub is a real API with a
# documented rate limit (60/min free), unlike yfinance's scraper which Yahoo
# throttles by IP. Used as the primary source whenever FINNHUB_API_KEY is set.
FINNHUB_MAP: dict[str, str] = {
    "forward_pe": "forwardPE",
    "trailing_pe": "peExclExtraTTM",
    "price_to_book": "pb",
    "price_to_sales": "psTTM",
    "peg_ratio": "forwardPEG",
    "market_cap": "marketCapitalization",  # Finnhub reports MILLIONS — scaled below
    "dividend_yield": "dividendYieldIndicatedAnnual",
    "beta": "beta",
    "eps": "epsTTM",
    "profit_margin": "netProfitMarginTTM",
    "revenue_growth": "revenueGrowthTTMYoy",
    "debt_to_equity": "longTermDebt/equityQuarterly",
    # current_price isn't in /stock/metric; falls through to None (or yfinance).
}

# `QuantCondition.operator` (VARCHAR(2)) -> comparison.
_OPS = {
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "=": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def clear_cache() -> None:
    """Drop the metric cache (tests / a forced refresh)."""
    _cache.clear()


def _is_rate_limited(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(marker in msg for marker in _RATE_LIMIT_MARKERS)


def _all_none() -> dict[str, float | None]:
    return {metric: None for metric in METRIC_MAP}


def _coerce(raw) -> float | None:
    return float(raw) if isinstance(raw, (int, float)) and not isinstance(raw, bool) else None


def _fetch_from_finnhub(ticker: str) -> dict[str, float | None]:
    """One Finnhub /stock/metric lookup, normalized to the backend metric names.
    Raises on HTTP error (incl. 429 rate-limit, which triggers backoff upstream)."""
    resp = requests.get(
        f"{FINNHUB_BASE}/stock/metric",
        params={"symbol": ticker, "metric": "all", "token": settings.FINNHUB_API_KEY},
        timeout=10,
    )
    resp.raise_for_status()
    metric = resp.json().get("metric", {}) or {}
    values: dict[str, float | None] = {}
    for name, field in FINNHUB_MAP.items():
        values[name] = _coerce(metric.get(field))
    # Finnhub market cap is in millions; scale to raw dollars to match yfinance.
    if values.get("market_cap") is not None:
        values["market_cap"] *= 1_000_000
    # Any metric Finnhub doesn't carry (e.g. current_price) stays absent -> None.
    for name in METRIC_MAP:
        values.setdefault(name, None)
    return values


def _fetch_from_yfinance(ticker: str) -> dict[str, float | None]:
    """One raw yfinance lookup, normalized to the backend metric names. May raise
    (network / rate-limit); an empty `.info` returns all-None without raising."""
    import yfinance as yf  # lazy: optional dependency
    info = yf.Ticker(ticker).info or {}
    return {metric: _coerce(info.get(yf_key)) for metric, yf_key in METRIC_MAP.items()}


def _fetch_raw(ticker: str) -> dict[str, float | None]:
    """Finnhub when a key is configured (reliable, rate-limit-documented),
    else the keyless yfinance scraper."""
    if settings.FINNHUB_API_KEY:
        return _fetch_from_finnhub(ticker)
    return _fetch_from_yfinance(ticker)


def _fetch_with_retry(ticker: str) -> dict[str, float | None]:
    """Fetch with exponential backoff on rate-limit errors. Any other failure, or
    exhausted retries, degrades to all-None so the evaluator says *incomplete*
    rather than crashing the loop."""
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return _fetch_raw(ticker)
        except Exception as exc:
            if _is_rate_limited(exc) and attempt < _MAX_RETRIES:
                delay = _BACKOFF_BASE_SECONDS * (2 ** attempt)
                logger.warning("quant: %s rate-limited — backing off %.1fs (attempt %d/%d)",
                               ticker, delay, attempt + 1, _MAX_RETRIES + 1)
                time.sleep(delay)
                continue
            logger.warning("quant: yfinance lookup failed for %s: %s", ticker, exc)
            return _all_none()
    return _all_none()


def fetch_metrics(ticker: str, ttl: float | None = None) -> dict[str, float | None]:
    """Live metric values for one ticker, keyed by backend metric name.

    Cached per ticker for `ttl` seconds (default `QUANT_CACHE_TTL_SECONDS`) — this
    both cuts yfinance calls across cycles and dedups repeat tickers within a
    cycle. Rate-limit (429) errors are retried with backoff. Best-effort: a
    missing metric or an exhausted retry comes back as ``None`` so the evaluator
    marks the condition *incomplete* rather than false. Never raises.
    """
    ttl = settings.QUANT_CACHE_TTL_SECONDS if ttl is None else ttl
    now = time.monotonic()

    cached = _cache.get(ticker)
    if cached is not None and cached[0] > now:
        logger.debug("quant: cache hit for %s", ticker)
        return cached[1]

    values = _fetch_with_retry(ticker)

    # Only cache a lookup that returned real data — caching an all-None failure
    # would suppress retries for the whole TTL and pin a ticker to 'incomplete'.
    if ttl > 0 and any(v is not None for v in values.values()):
        _cache[ticker] = (now + ttl, values)
    return values


def evaluate_conditions(conditions, metric_values: dict[str, float | None]) -> list[dict]:
    """Compare each condition against fetched metric values, aligned by position.

    Args:
        conditions: ordered iterable of `QuantCondition` rows (need `.metric`,
            `.operator`, `.value`, `.enabled`). Order MUST match the
            `thesis["quant_conditions"]` list the adapter builds.
        metric_values: output of `fetch_metrics`.

    Returns:
        One `{"value", "passes"}` dict per condition, in the same order.
    """
    results: list[dict] = []
    for c in conditions:
        value = metric_values.get(c.metric)
        op = _OPS.get(c.operator)
        if value is None or op is None:
            if op is None:
                logger.warning("quant: unsupported operator %r on metric %r", c.operator, c.metric)
            results.append({"value": value, "passes": None})
            continue
        threshold = float(c.value)
        results.append({"value": value, "passes": bool(op(value, threshold))})
    return results
