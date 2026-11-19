"""Quick test: generate a grounded weather report from sample stats with Gemini."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()

MODEL = "gemini-3.5-flash-lite"

# Stand-in for the stats engine output (Task 5)
SAMPLE_STATS = {
    "report_time_local": "2026-01-15 07:00",
    "current": {
        "temperature_c": -6.0,
        "humidity_pct": 82,
        "pressure_hpa": 1006.2,
        "wind_speed_kmh": 20,
        "wind_direction": "NW",
        "feels_like_c": -12.0,
        "feels_like_type": "wind_chill",
    },
    "vs_yesterday": {
        "temperature_c": {"change": 4.0, "direction": "lower"},
        "humidity_pct": {"change": 12, "direction": "higher"},
        "pressure_hpa": {"change": 6.6, "direction": "lower"},
        "wind_speed_kmh": {"change": 12, "direction": "higher"},
    },
    "trend_7_day": {
        "temperature_c": {"mean": -3.0, "direction": "falling"},
        "humidity_pct": {"mean": 74, "direction": "steady"},
        "pressure_hpa": {"mean": 1011.5, "direction": "falling"},
        "wind_speed_kmh": {"mean": 11, "direction": "steady"},
    },
    "pressure_change_3h_hpa": -2.4,
    "data_quality": {"completeness_pct": 100, "missing_sensors": []},
}

GROUNDING_RULES = """You write short daily weather reports for someone camping outdoors.

Rules:
- Use only numbers that appear in the input data. Never calculate new numbers.
- Use the direction words given in the input ("higher", "falling", etc.) and never contradict them.
- State the time reference for every comparison, such as "this time yesterday" or "over the past 7 days".
- Do not forecast future weather.
- Do not mention information that is not in the input, such as regional forecasts or causes.
- If a value is missing or null, say it is unavailable.
- Keep the whole report under 150 words, in plain, calm language.
- For each claim you make, record the input field it comes from in the claims list.
Style:
- Write like a friendly weather update, not a list of numbers. Lead with how it feels outside.
- You may use plain descriptive words that follow directly from the data, like "cold", "damp", or "breezy".
- In the comparison and trend sections, mention at most the two most notable changes, not every measurement.
- Write units naturally: °C, km/h, hPa. Describe humidity changes as "more humid" or in percentage points, never as a percent change."""

class Claim(BaseModel):
    text: str
    source_field: str


class WeatherReport(BaseModel):
    current_conditions: str
    feels_like: str
    vs_yesterday: str
    recent_trend: str
    claims: list[Claim]


def main():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    response = client.models.generate_content(
        model=MODEL,
        contents=f"Write the report from this data:\n{json.dumps(SAMPLE_STATS, indent=2)}",
        config=types.GenerateContentConfig(
            system_instruction=GROUNDING_RULES,
            response_mime_type="application/json",
            response_schema=WeatherReport,
        ),
    )

    report: WeatherReport = response.parsed
    print(json.dumps(report.model_dump(), indent=2, ensure_ascii=False))

    output = Path("data/reports/sample_report.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"input": SAMPLE_STATS, "report": report.model_dump()}, indent=2)
    )
    print(f"\nSaved to {output}")


if __name__ == "__main__":
    main()
