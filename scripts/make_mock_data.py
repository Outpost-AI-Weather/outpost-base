"""Convert ECCC hourly climate CSVs into decoder-format JSON Lines mock data."""

import argparse
import json
import struct
from pathlib import Path

import numpy as np
import pandas as pd

# Packet layout from the interface spec, little-endian, 23 bytes
PACKET_FORMAT = "<BBHIhHIHHHB"
PROTOCOL_VERSION = 1
NODE_ID = 1
BATTERY_MV = 12500

# ECCC times are local standard time, which is always UTC-5 for Toronto
LST_TO_UTC = pd.Timedelta(hours=5)

# Reserved values meaning "no reading"
RESERVED_INT16 = 0x7FFF
RESERVED_UINT16 = 0xFFFF
RESERVED_UINT32 = 0xFFFFFFFF

FAULT_BITS = {
    "temperature": 0,
    "humidity": 1,
    "pressure": 2,
    "wind_speed": 3,
    "wind_direction": 4,
    "low_battery": 5,
    "clock_not_synced": 6,
}


def value_or_none(value):
    """Turn pandas' missing values into None."""
    return None if pd.isna(value) else float(value)


def scaled(value, factor, reserved):
    """Convert a real value to the packet's scaled integer, or the reserved value if missing."""
    return reserved if value is None else round(value * factor)


def convert_row(row, sequence):
    utc_time = (pd.Timestamp(row["Date/Time (LST)"]) + LST_TO_UTC).tz_localize("UTC")

    temperature = value_or_none(row["Temp (°C)"])
    humidity = value_or_none(row["Rel Hum (%)"])
    pressure_kpa = value_or_none(row["Stn Press (kPa)"])
    wind_kmh = value_or_none(row["Wind Spd (km/h)"])
    wind_dir_tens = value_or_none(row["Wind Dir (10s deg)"])

    pressure_pa = round(pressure_kpa * 1000) if pressure_kpa is not None else None
    wind_speed_ms = round(wind_kmh / 3.6, 2) if wind_kmh is not None else None
    # 0 means calm (no direction); 36 means north, stored as 0 degrees
    wind_direction_deg = (wind_dir_tens * 10) % 360 if wind_dir_tens else None

    # A missing sensor value counts as a fault. Calm wind direction does not.
    faults = []
    for name, value in [
        ("temperature", temperature),
        ("humidity", humidity),
        ("pressure", pressure_pa),
        ("wind_speed", wind_speed_ms),
    ]:
        if value is None:
            faults.append(name)
    status_flags = sum(1 << FAULT_BITS[name] for name in faults)

    sequence = sequence % 65536
    node_timestamp = int(utc_time.timestamp())

    payload = struct.pack(
        PACKET_FORMAT,
        PROTOCOL_VERSION,
        NODE_ID,
        sequence,
        node_timestamp,
        scaled(temperature, 100, RESERVED_INT16),
        scaled(humidity, 100, RESERVED_UINT16),
        scaled(pressure_pa, 1, RESERVED_UINT32),
        scaled(wind_speed_ms, 100, RESERVED_UINT16),
        scaled(wind_direction_deg, 10, RESERVED_UINT16),
        BATTERY_MV,
        status_flags,
    )

    return {
        "protocol_version": PROTOCOL_VERSION,
        "node_id": NODE_ID,
        "sequence": sequence,
        "node_timestamp": node_timestamp,
        "received_at": utc_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "temperature_c": temperature,
        "humidity_pct": humidity,
        "pressure_pa": pressure_pa,
        "wind_speed_ms": wind_speed_ms,
        "wind_direction_deg": wind_direction_deg,
        "battery_mv": BATTERY_MV,
        "status_flags": status_flags,
        "faults": faults,
        "rssi_dbm": None,
        "snr_db": None,
        "raw_payload_hex": payload.hex(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="ECCC hourly CSV files")
    parser.add_argument("--output", default="data/mock/mock_readings.jsonl")
    parser.add_argument("--reference", default="data/mock/reference_feels_like.csv")
    parser.add_argument("--messy", action="store_true", help="add realistic data problems")
    parser.add_argument("--seed", type=int, default=42, help="random seed for --messy")
    args = parser.parse_args()

    df = pd.concat([pd.read_csv(path) for path in args.inputs], ignore_index=True)
    df = df.sort_values("Date/Time (LST)").reset_index(drop=True)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    if args.messy:
        # Humidity is read as integers, which can't hold missing values
        df["Rel Hum (%)"] = df["Rel Hum (%)"].astype(float)
        # Sensor fault: humidity missing for 6 hours
        df.loc[100:105, "Rel Hum (%)"] = np.nan
        # Implausible reading that ingest should reject
        df.loc[200, "Temp (°C)"] = 85.0

    readings = [convert_row(row, sequence) for sequence, row in df.iterrows()]

    if args.messy:
        rng = np.random.default_rng(args.seed)
        # Lost packets: drop about 2%, leaving gaps in the sequence numbers
        keep = rng.random(len(readings)) > 0.02
        readings = [r for r, k in zip(readings, keep) if k]
        # Duplicate packet
        readings.insert(51, dict(readings[50]))

    with output.open("w") as f:
        for reading in readings:
            f.write(json.dumps(reading) + "\n")

    with_faults = sum(1 for r in readings if r["faults"])
    print(f"Wrote {len(readings)} readings to {output}")
    print(f"Readings with missing values: {with_faults}")

    # ECCC's official feels-like values, for testing the stats engine later
    if not args.messy:
        reference = pd.DataFrame(
            {
                "received_at": [r["received_at"] for r in readings],
                "temperature_c": df["Temp (°C)"],
                "dew_point_c": df["Dew Point Temp (°C)"],
                "humidity_pct": df["Rel Hum (%)"],
                "wind_speed_kmh": df["Wind Spd (km/h)"],
                "eccc_humidex": df["Hmdx"],
                "eccc_wind_chill": df["Wind Chill"],
            }
        )
        reference.to_csv(args.reference, index=False)
        print(f"Wrote reference values to {args.reference}")

if __name__ == "__main__":
    main()