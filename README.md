# AI Momentum Trading Platform

Modular Python trading research and execution system inspired by the HKUDS Vibe-Trading multi-agent workflow. It scans momentum stocks, detects unusual volume, builds technical and sentiment context, generates AI-assisted signals, sizes risk, backtests strategies, journals decisions, and can route paper orders through Alpaca.

This is engineering infrastructure, not financial advice. Start in paper mode and validate every strategy before enabling live trading.

## Architecture

- `orchestration/`: Vibe-Trading adapter plus local multi-agent coordinator.
- `agents/`: momentum, volume, technical, sentiment, options-flow, risk, execution, and journal agents.
- `data/options_client.py`: Alpaca options chain, IV, Greeks, and derived activity scoring.
- `data/`: Alpha Vantage client, Alpaca client, Redis/local cache, and technical indicators.
- `strategies/`: momentum, breakout, gap-and-go, and Pine Script export.
- `backtesting/`: event-driven engine, metrics, and walk-forward optimizer.
- `api/`: FastAPI service for scans, signals, account, orders, and backtests.
- `dashboard/`: Streamlit trading desk.
- `database/`: SQLAlchemy models for signals, trades, snapshots, performance, and AI logs.
- `alerts/`: Telegram and Discord alert senders.

## Quick Start

```bash
cp .env.example .env
# edit .env with paper API keys
docker compose up --build
```

Services:

- FastAPI: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Streamlit: `http://localhost:8501`
- Postgres: `localhost:5432`
- Redis: `localhost:6379`

Local Python:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn api.main:app --reload
streamlit run dashboard/streamlit_app.py
```

## Required Keys

Set these in `.env`:

- `OPENAI_API_KEY`
- `ALPHA_VANTAGE_API_KEY`
- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

`ENABLE_MOCK_DATA=true` allows the system to run without market-data keys while you develop.

## Vibe-Trading Integration

The project uses a `VibeTradingOrchestrator` as the AI orchestration boundary. By default it runs local agents. If you expose a local Vibe-Trading service, set:

```bash
VIBE_TRADING_ENDPOINT=http://localhost:8899
```

When delegation fails or is not configured, local agents continue to run.

## API Examples

```bash
curl http://localhost:8000/health
curl "http://localhost:8000/scan?symbols=NVDA,TSLA,AMD"
curl "http://localhost:8000/signals/NVDA"
curl "http://localhost:8000/options/AAPL?expiration_days=45&option_type=all&min_unusual_score=60"
curl -X POST http://localhost:8000/backtest -H "Content-Type: application/json" -d "{\"symbol\":\"NVDA\"}"
```

Paper order example:

```bash
curl -X POST http://localhost:8000/orders ^
  -H "Content-Type: application/json" ^
  -d "{\"symbol\":\"AAPL\",\"qty\":1,\"side\":\"buy\",\"order_type\":\"market\"}"
```

Live trading is blocked unless `ENABLE_LIVE_TRADING=true`.

## Signal Logic

BUY requires:

- Relative volume greater than `3`
- Price above VWAP
- EMA9 above EMA20
- RSI between `55` and `75`
- Bullish sentiment score above `0.7`
- Bullish market trend flag

SELL can trigger when:

- Momentum weakens
- Volume declines
- RSI divergence is detected
- Stop loss is triggered by risk controls

## Options Chain And Activity Scoring

The `/options/{symbol}` endpoint fetches Alpaca option-chain snapshots and returns:

- Calls and puts by expiration and strike
- Bid, ask, mid, spread, and quote size
- Latest trade price and size when available
- Implied volatility and Greeks
- Derived unusual activity score
- Call/put premium and activity imbalance

Example:

```bash
curl "http://localhost:8000/options/TSLA?option_type=call&expiration_days=30&min_iv=0.2&max_delta=0.8&min_unusual_score=50"
```

The dashboard includes the same filters in the sidebar. Activity scoring uses snapshot quote size, latest trade size, premium proxy, IV percentile, spread quality, and Greeks. It is useful for screening but should not be treated as full OPRA tape reconstruction.

## Testing

```bash
pytest
```

The current tests cover indicators, risk sizing, performance metrics, and signal generation. Add integration tests with API keys only against paper trading.
