"""Generate a grounded weather report from real stats with Gemini."""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from sqlmodel import Session

from outpost_base.db.session import engine
from outpost_base.stats.builder import build_stats

load_dotenv()

MODEL = "gemini-3.5-flash-lite"

GROUNDING_RULES = """You write short daily weather reports for someone camping outdoors.

Rules:
- Use only numbers that appear in the input data. Never calculate new numbers.
- Use the direction words given in the input ("higher", "falling", etc.) and never contradict them.
  "about the same" means there was no meaningful change.
- State the time reference for every comparison, such as "this time yesterday" or "over the past 7 days".
- For the trend, if days_available is fewer than 7, say the actual number of days instead.
- Do not forecast future weather. If rapid_drop is true, you may say pressure has dropped quickly
  over the last 3 hours, as a fact only.
- Do not mention information that is not in the input, such as regional forecasts or causes.
- If a value is missing or null, say it is unavailable.
- If station_online is false, say only that the station is offline and no current report is available.
- Keep the whole report under 150 words, in plain, calm language.
- For each claim you make, record the input field it comes from in the claims list.
- Each claim's text must be the shortest phrase from the report containing that one fact,
  for example "-14.1 °C" or "lower by 18.0 °C", never a whole sentence.

Style:
- Write like a friendly weather update, not a list of numbers. Lead with how it feels outside.
- You may use plain descriptive words that follow directly from the data, like "cold", "damp", or "breezy".
- In the comparison and trend sections, mention at most the two most notable changes, not every measurement.
- Write units naturally: °C, km/h, hPa. Describe humidity changes as "more humid" or in percentage points,
  never as a percent change."""


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--at", default="2026-01-15T12:00:00+00:00", help="UTC time, ISO 8601")
    parser.add_argument("--node", type=int, default=1)
    args = parser.parse_args()

    with Session(engine) as session:
        stats = build_stats(session, args.node, datetime.fromisoformat(args.at))

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=MODEL,
        contents=f"Write the report from this data:\n{json.dumps(stats, indent=2)}",
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
        json.dumps({"input": stats, "report": report.model_dump()}, indent=2, ensure_ascii=False)
    )
    print(f"\nSaved to {output}")


if __name__ == "__main__":
    main()
