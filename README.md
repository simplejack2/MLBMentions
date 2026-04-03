# MLB Mentions — Kalshi Betting Model Scaffold

A starter scaffold for an MLB mentions betting model focused on Kalshi markets.

## Included

- `app/schemas/market.py` — normalized market schema
- `app/data_sources/kalshi_client.py` — direct HTTP client for public Kalshi market data
- `app/parsers/market_family_classifier.py` — market-family classifier for MLB mentions markets
- `app/ranking/edge.py` — odds and edge math helpers
- `app/main.py` — starter pipeline that fetches, filters, classifies, and prints a board

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

## Run

```bash
python -m app.main
```

## Notes

- Uses direct HTTP requests for public Kalshi market data (no auth required).
- Does not place trades.
- Does not yet join MLB schedule, rosters, lineups, or announcers.

## Next suggested files

- `app/schemas/game.py`
- `app/data_sources/mlb_client.py`
- `app/features/global_features.py`
- `app/models/bunt_model.py`
- `app/models/bases_loaded_model.py`
- `app/models/grand_slam_model.py`
- `app/ranking/ranker.py`
