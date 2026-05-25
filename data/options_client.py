from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Literal

from config.settings import Settings


OptionType = Literal["call", "put", "all"]


@dataclass(slots=True)
class OptionsChainFilters:
    option_type: OptionType = "all"
    expiration_date_gte: date | None = None
    expiration_date_lte: date | None = None
    strike_min: float | None = None
    strike_max: float | None = None
    min_iv: float | None = None
    max_iv: float | None = None
    min_delta: float | None = None
    max_delta: float | None = None
    min_gamma: float | None = None
    max_gamma: float | None = None
    min_unusual_score: float = 0.0
    limit: int = 250


class AlpacaOptionsClient:
    """Fetches and normalizes Alpaca options-chain snapshots."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = None
        if settings.alpaca_api_key and settings.alpaca_secret_key:
            from alpaca.data.historical.option import OptionHistoricalDataClient

            self._client = OptionHistoricalDataClient(
                settings.alpaca_api_key,
                settings.alpaca_secret_key,
            )

    async def get_chain(self, symbol: str, filters: OptionsChainFilters | None = None) -> dict[str, Any]:
        filters = filters or OptionsChainFilters()
        if self._client is None:
            if self.settings.enable_mock_data:
                rows = self._mock_chain(symbol)
                return self._build_response(symbol, self._apply_filters(rows, filters), filters)
            raise RuntimeError("Alpaca options data requires ALPACA_API_KEY and ALPACA_SECRET_KEY.")

        raw_chain = await asyncio.to_thread(self._fetch_chain, symbol.upper(), filters)
        rows = [self._normalize_snapshot(symbol.upper(), contract_symbol, snapshot) for contract_symbol, snapshot in raw_chain.items()]
        rows = [row for row in rows if row is not None]
        scored = self._score_rows(rows)
        filtered = self._apply_filters(scored, filters)
        return self._build_response(symbol.upper(), filtered, filters)

    def _fetch_chain(self, symbol: str, filters: OptionsChainFilters) -> dict[str, Any]:
        from alpaca.data.enums import OptionsFeed
        from alpaca.data.requests import OptionChainRequest
        from alpaca.trading.enums import ContractType

        option_type = None
        if filters.option_type == "call":
            option_type = ContractType.CALL
        elif filters.option_type == "put":
            option_type = ContractType.PUT

        request = OptionChainRequest(
            underlying_symbol=symbol,
            feed=OptionsFeed.INDICATIVE,
            type=option_type,
            strike_price_gte=filters.strike_min,
            strike_price_lte=filters.strike_max,
            expiration_date_gte=(filters.expiration_date_gte or date.today()).isoformat(),
            expiration_date_lte=(filters.expiration_date_lte or (date.today() + timedelta(days=45))).isoformat(),
        )
        return self._client.get_option_chain(request)

    def _normalize_snapshot(self, underlying: str, contract_symbol: str, snapshot: Any) -> dict[str, Any] | None:
        raw = snapshot.model_dump(mode="json") if hasattr(snapshot, "model_dump") else dict(snapshot)
        parsed = parse_option_symbol(contract_symbol)
        if parsed is None:
            return None

        quote = raw.get("latest_quote") or {}
        trade = raw.get("latest_trade") or {}
        greeks = raw.get("greeks") or {}
        bid = _as_float(quote.get("bid_price"))
        ask = _as_float(quote.get("ask_price"))
        bid_size = _as_float(quote.get("bid_size"))
        ask_size = _as_float(quote.get("ask_size"))
        last_price = _as_float(trade.get("price"))
        last_size = _as_float(trade.get("size"))
        mid = _mid_price(bid, ask, last_price)
        spread = ask - bid if ask and bid else None
        spread_pct = spread / mid if spread is not None and mid else None
        total_quote_size = bid_size + ask_size
        activity_proxy = max(total_quote_size, last_size)
        premium_proxy = mid * activity_proxy * 100 if mid else 0.0
        expiration = parsed["expiration_date"]

        return {
            "underlying_symbol": underlying,
            "contract_symbol": contract_symbol,
            "option_type": parsed["option_type"],
            "expiration_date": expiration.isoformat(),
            "days_to_expiration": max((expiration - date.today()).days, 0),
            "strike": parsed["strike"],
            "bid": bid,
            "ask": ask,
            "mid": mid,
            "spread": spread,
            "spread_pct": spread_pct,
            "bid_size": bid_size,
            "ask_size": ask_size,
            "total_quote_size": total_quote_size,
            "last_price": last_price,
            "last_size": last_size,
            "activity_proxy": activity_proxy,
            "premium_proxy": premium_proxy,
            "implied_volatility": _as_float(raw.get("implied_volatility")),
            "delta": _as_float(greeks.get("delta")),
            "gamma": _as_float(greeks.get("gamma")),
            "theta": _as_float(greeks.get("theta")),
            "vega": _as_float(greeks.get("vega")),
            "rho": _as_float(greeks.get("rho")),
            "quote_timestamp": quote.get("timestamp"),
            "trade_timestamp": trade.get("timestamp"),
        }

    def _score_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return rows

        median_activity = _median([row["activity_proxy"] for row in rows if row["activity_proxy"]])
        median_premium = _median([row["premium_proxy"] for row in rows if row["premium_proxy"]])
        iv_values = sorted(row["implied_volatility"] for row in rows if row["implied_volatility"] is not None)

        for row in rows:
            activity_ratio = row["activity_proxy"] / median_activity if median_activity else 0.0
            premium_ratio = row["premium_proxy"] / median_premium if median_premium else 0.0
            iv_rank = _percent_rank(iv_values, row["implied_volatility"])
            trade_component = min(row["last_size"] / 100, 1.0) if row["last_size"] else 0.0
            spread_quality = 1.0 - min(row["spread_pct"] or 1.0, 1.0)
            score = (
                28 * min(math.log1p(activity_ratio) / math.log(6), 1.0)
                + 32 * min(math.log1p(premium_ratio) / math.log(8), 1.0)
                + 18 * iv_rank
                + 12 * trade_component
                + 10 * max(spread_quality, 0.0)
            )
            row["activity_ratio"] = round(activity_ratio, 3)
            row["premium_ratio"] = round(premium_ratio, 3)
            row["iv_percentile"] = round(iv_rank, 3)
            row["unusual_activity_score"] = round(min(score, 100.0), 2)
            row["liquidity_bias"] = _liquidity_bias(row["bid_size"], row["ask_size"])
        return rows

    def _apply_filters(self, rows: list[dict[str, Any]], filters: OptionsChainFilters) -> list[dict[str, Any]]:
        filtered = []
        for row in rows:
            if filters.option_type != "all" and row["option_type"] != filters.option_type:
                continue
            if filters.min_iv is not None and (row["implied_volatility"] is None or row["implied_volatility"] < filters.min_iv):
                continue
            if filters.max_iv is not None and row["implied_volatility"] is not None and row["implied_volatility"] > filters.max_iv:
                continue
            if filters.min_delta is not None and (row["delta"] is None or row["delta"] < filters.min_delta):
                continue
            if filters.max_delta is not None and row["delta"] is not None and row["delta"] > filters.max_delta:
                continue
            if filters.min_gamma is not None and (row["gamma"] is None or row["gamma"] < filters.min_gamma):
                continue
            if filters.max_gamma is not None and row["gamma"] is not None and row["gamma"] > filters.max_gamma:
                continue
            if row.get("unusual_activity_score", 0) < filters.min_unusual_score:
                continue
            filtered.append(row)

        filtered.sort(key=lambda item: item.get("unusual_activity_score", 0), reverse=True)
        return filtered[: max(filters.limit, 1)]

    def _build_response(self, symbol: str, rows: list[dict[str, Any]], filters: OptionsChainFilters) -> dict[str, Any]:
        summary = summarize_options_activity(rows)
        return {
            "symbol": symbol.upper(),
            "contract_count": len(rows),
            "summary": summary,
            "contracts": rows,
            "filters": {
                "option_type": filters.option_type,
                "expiration_date_gte": filters.expiration_date_gte.isoformat() if filters.expiration_date_gte else None,
                "expiration_date_lte": filters.expiration_date_lte.isoformat() if filters.expiration_date_lte else None,
                "strike_min": filters.strike_min,
                "strike_max": filters.strike_max,
                "min_iv": filters.min_iv,
                "max_iv": filters.max_iv,
                "min_delta": filters.min_delta,
                "max_delta": filters.max_delta,
                "min_gamma": filters.min_gamma,
                "max_gamma": filters.max_gamma,
                "min_unusual_score": filters.min_unusual_score,
                "limit": filters.limit,
            },
        }

    def _mock_chain(self, symbol: str) -> list[dict[str, Any]]:
        today = date.today()
        rows = []
        for idx, option_type in enumerate(["call", "put"]):
            for offset, strike in enumerate([95, 100, 105, 110]):
                mid = 1.2 + offset * 0.45 + idx * 0.2
                rows.append(
                    {
                        "underlying_symbol": symbol.upper(),
                        "contract_symbol": f"{symbol.upper()}{today:%y%m%d}{option_type[0].upper()}{int(strike * 1000):08d}",
                        "option_type": option_type,
                        "expiration_date": (today + timedelta(days=14 + offset * 7)).isoformat(),
                        "days_to_expiration": 14 + offset * 7,
                        "strike": float(strike),
                        "bid": mid - 0.05,
                        "ask": mid + 0.05,
                        "mid": mid,
                        "spread": 0.1,
                        "spread_pct": 0.1 / mid,
                        "bid_size": 80 + offset * 15,
                        "ask_size": 120 + offset * 25,
                        "total_quote_size": 200 + offset * 40,
                        "last_price": mid,
                        "last_size": 25 + offset * 10,
                        "activity_proxy": 200 + offset * 40,
                        "premium_proxy": mid * (200 + offset * 40) * 100,
                        "implied_volatility": 0.35 + offset * 0.05,
                        "delta": 0.55 if option_type == "call" else -0.45,
                        "gamma": 0.03,
                        "theta": -0.02,
                        "vega": 0.08,
                        "rho": 0.01,
                        "quote_timestamp": datetime.utcnow().isoformat(),
                        "trade_timestamp": datetime.utcnow().isoformat(),
                    }
                )
        return self._score_rows(rows)


def summarize_options_activity(rows: list[dict[str, Any]]) -> dict[str, Any]:
    calls = [row for row in rows if row["option_type"] == "call"]
    puts = [row for row in rows if row["option_type"] == "put"]
    call_premium = sum(row["premium_proxy"] for row in calls)
    put_premium = sum(row["premium_proxy"] for row in puts)
    call_activity = sum(row["activity_proxy"] for row in calls)
    put_activity = sum(row["activity_proxy"] for row in puts)
    premium_ratio = call_premium / put_premium if put_premium else None
    activity_ratio = call_activity / put_activity if put_activity else None
    top_contract = max(rows, key=lambda row: row.get("unusual_activity_score", 0), default=None)
    bias = "neutral"
    if premium_ratio is not None:
        if premium_ratio >= 1.25:
            bias = "call_heavy"
        elif premium_ratio <= 0.8:
            bias = "put_heavy"

    return {
        "call_contracts": len(calls),
        "put_contracts": len(puts),
        "call_premium_proxy": round(call_premium, 2),
        "put_premium_proxy": round(put_premium, 2),
        "call_put_premium_ratio": round(premium_ratio, 3) if premium_ratio is not None else None,
        "call_put_activity_ratio": round(activity_ratio, 3) if activity_ratio is not None else None,
        "flow_bias": bias,
        "avg_iv": round(_mean([row["implied_volatility"] for row in rows if row["implied_volatility"] is not None]), 4),
        "top_contract": top_contract["contract_symbol"] if top_contract else None,
        "top_unusual_activity_score": top_contract.get("unusual_activity_score") if top_contract else None,
        "note": "Activity uses Alpaca snapshot size, latest trade size, premium, IV, and Greeks as a proxy; it is not full OPRA tape flow.",
    }


def parse_option_symbol(contract_symbol: str) -> dict[str, Any] | None:
    if len(contract_symbol) < 16:
        return None
    suffix = contract_symbol[-15:]
    root = contract_symbol[:-15]
    try:
        expiration = datetime.strptime(suffix[:6], "%y%m%d").date()
        option_type = "call" if suffix[6] == "C" else "put" if suffix[6] == "P" else None
        strike = int(suffix[7:]) / 1000
    except ValueError:
        return None
    if not root or option_type is None:
        return None
    return {"root": root, "expiration_date": expiration, "option_type": option_type, "strike": strike}


def _as_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _mid_price(bid: float, ask: float, last_price: float) -> float:
    if bid > 0 and ask > 0:
        return (bid + ask) / 2
    if ask > 0:
        return ask
    if bid > 0:
        return bid
    return last_price


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _percent_rank(values: list[float], value: float | None) -> float:
    if not values or value is None:
        return 0.0
    below_or_equal = sum(1 for item in values if item <= value)
    return below_or_equal / len(values)


def _liquidity_bias(bid_size: float, ask_size: float) -> str:
    if bid_size <= 0 and ask_size <= 0:
        return "unknown"
    if bid_size >= ask_size * 1.5:
        return "bid_heavy"
    if ask_size >= bid_size * 1.5:
        return "ask_heavy"
    return "balanced"

