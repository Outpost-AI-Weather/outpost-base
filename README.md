# Outpost Base Station

Base station software for the Outpost field weather station. Receives sensor data, stores readings, computes statistics, generates AI weather reports, and serves the API for the dashboard.

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone git@github.com:Outpost-AI-Weather/outpost-base.git
cd outpost-base
uv sync
cp .env.example .env   # then fill in your API keys
mkdir data
```

## Running

Start the API server:

```bash
uv run uvicorn outpost_base.api.main:app --reload
```

Then open http://127.0.0.1:8000/docs for the interactive API docs.

## Testing

```bash
uv run pytest
uv run ruff check
```

## Mock data

Mock readings are generated from Environment and Climate Change Canada hourly data for Toronto Pearson (station TORONTO INTL A, Climate ID 6158731), in the decoder output format.

1. Download hourly CSVs from https://climate.weather.gc.ca/historical_data/search_historic_data_e.html for January 2026 and July 2026, and save them as `data/raw/toronto_2026_01.csv` and `data/raw/toronto_2026_07.csv`
2. Generate the clean and messy datasets:

```bash
uv run python scripts/make_mock_data.py data/raw/toronto_2026_01.csv data/raw/toronto_2026_07.csv
uv run python scripts/make_mock_data.py data/raw/toronto_2026_01.csv data/raw/toronto_2026_07.csv --messy --output data/mock/mock_readings_messy.jsonl
```

| Output | Contents |
|---|---|
| `data/mock/mock_readings.jsonl` | Clean readings, one per line, including the binary packet as hex |
| `data/mock/mock_readings_messy.jsonl` | Same data with lost packets, a 6-hour humidity fault, an 85°C bad reading, and a duplicate packet |
| `data/mock/reference_feels_like.csv` | ECCC's official humidex and wind chill values, for testing the stats engine |

Conversions: local standard time + 5 h → UTC, kPa × 1000 → Pa, km/h ÷ 3.6 → m/s, wind direction tens of degrees × 10 → degrees (0 = calm → null).

## Project structure

| Folder | Purpose |
|---|---|
| `src/outpost_base/decoder/` | Converts raw LoRa packets into JSON |
| `src/outpost_base/ingest/` | Validates and saves readings |
| `src/outpost_base/db/` | Database models |
| `src/outpost_base/stats/` | Stats engine |
| `src/outpost_base/reports/` | AI report generation and validation |
| `src/outpost_base/api/` | API endpoints |
| `scripts/` | Mock data and utility scripts |
| `tests/` | Tests |