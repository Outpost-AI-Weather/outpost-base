"""Compare our feels-like calculations with ECCC's official values."""

import pandas as pd

from outpost_base.stats.feels_like import humidex_c, wind_chill_c

df = pd.read_csv("data/mock/reference_feels_like.csv")

for name, column, calculate in [
    ("Wind chill", "eccc_wind_chill", lambda r: wind_chill_c(r.temperature_c, r.wind_speed_kmh)),
    ("Humidex", "eccc_humidex", lambda r: humidex_c(r.temperature_c, r.humidity_pct)),
]:
    rows = df[df[column].notna()]
    ours = rows.apply(calculate, axis=1)
    compared = ours.notna()
    differences = (ours[compared].round() - rows.loc[compared, column]).abs()

    print(f"{name}:")
    print(f"  ECCC reported:      {len(rows)} hours")
    print(f"  We also calculated: {compared.sum()} of those")
    print(f"  Exact match:        {(differences == 0).mean():.1%}")
    print(f"  Within 1 degree:    {(differences <= 1).mean():.1%}")
    print(f"  Largest difference: {differences.max():.0f}")