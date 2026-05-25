from __future__ import annotations

import pandas as pd


OHLCV_COLUMNS = {"open", "high", "low", "close", "volume"}


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Return a sorted OHLCV frame with lowercase column names."""

    if df.empty:
        return df.copy()
    normalized = df.copy()
    normalized.columns = [str(col).lower().replace(" ", "_") for col in normalized.columns]
    rename_map = {
        "1._open": "open",
        "2._high": "high",
        "3._low": "low",
        "4._close": "close",
        "5._volume": "volume",
        "5._adjusted_close": "adjusted_close",
        "6._volume": "volume",
    }
    normalized = normalized.rename(columns=rename_map)
    if not isinstance(normalized.index, pd.DatetimeIndex):
        normalized.index = pd.to_datetime(normalized.index, utc=True, errors="coerce")
    normalized = normalized.sort_index()
    for col in OHLCV_COLUMNS.intersection(normalized.columns):
        normalized[col] = pd.to_numeric(normalized[col], errors="coerce")
    return normalized.dropna(subset=[col for col in ["open", "high", "low", "close"] if col in normalized])


def vwap(df: pd.DataFrame) -> pd.Series:
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    cumulative_volume = df["volume"].replace(0, pd.NA).cumsum()
    return (typical_price * df["volume"]).cumsum() / cumulative_volume


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    relative_strength = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + relative_strength))


def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    return pd.DataFrame(
        {
            "macd": macd_line,
            "macd_signal": signal_line,
            "macd_histogram": macd_line - signal_line,
        },
        index=series.index,
    )


def true_range(df: pd.DataFrame) -> pd.Series:
    previous_close = df["close"].shift(1)
    ranges = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    return true_range(df).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def bollinger_bands(series: pd.Series, period: int = 20, width: float = 2.0) -> pd.DataFrame:
    middle = series.rolling(period).mean()
    std = series.rolling(period).std()
    return pd.DataFrame(
        {
            "bb_upper": middle + width * std,
            "bb_middle": middle,
            "bb_lower": middle - width * std,
        },
        index=series.index,
    )


def relative_volume(df: pd.DataFrame, lookback: int = 20) -> pd.Series:
    average_volume = df["volume"].rolling(lookback).mean()
    return df["volume"] / average_volume.replace(0, pd.NA)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add standard technical indicators required by the agents."""

    enriched = normalize_ohlcv(df)
    if enriched.empty:
        return enriched

    enriched["vwap"] = vwap(enriched)
    for period in (9, 20, 50, 200):
        enriched[f"ema_{period}"] = ema(enriched["close"], period)
    enriched["rsi"] = rsi(enriched["close"])
    enriched = enriched.join(macd(enriched["close"]))
    enriched["atr"] = atr(enriched)
    enriched = enriched.join(bollinger_bands(enriched["close"]))
    enriched["relative_volume"] = relative_volume(enriched)
    return enriched


def price_above_vwap(row: pd.Series) -> bool:
    return bool(row.get("close", 0) > row.get("vwap", float("inf")))


def detect_rsi_divergence(df: pd.DataFrame, lookback: int = 10) -> bool:
    """Detect a simple bearish divergence over the most recent window."""

    if len(df) < lookback or "rsi" not in df:
        return False
    window = df.tail(lookback)
    price_higher_high = window["close"].iloc[-1] > window["close"].iloc[0]
    rsi_lower_high = window["rsi"].iloc[-1] < window["rsi"].iloc[0]
    return bool(price_higher_high and rsi_lower_high)

