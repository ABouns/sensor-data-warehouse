"""Generate IoT sensor data and bulk-load it into a normalised SQLite store.

Demonstrates data-storage practice:
  * a normalised schema (reference tables + a narrow fact table) defined in schema.sql
  * efficient bulk loading with executemany() inside a single transaction
  * a composite index for the dominant (sensor_id, ts) access pattern
  * a Parquet export of the fact table for columnar/analytical storage

Run:  python src/build_store.py
Outputs: data/sensors.db, data/readings.parquet
"""

from __future__ import annotations

import os
import sqlite3
import numpy as np
import pandas as pd

RNG = np.random.default_rng(2024)
DB = "data/sensors.db"
PARQUET = "data/readings.parquet"
SCHEMA = os.path.join(os.path.dirname(__file__), "..", "schema.sql")

CITIES = [
    ("Leuven", 50.879, 4.700),
    ("Brussels", 50.851, 4.357),
    ("Ghent", 51.054, 3.717),
    ("Antwerp", 51.219, 4.402),
]
SENSOR_TYPES = [
    ("temperature", "C", 12.0, 6.0),     # type, unit, mean, sd
    ("humidity", "%", 70.0, 12.0),
    ("pm25", "ug/m3", 18.0, 8.0),
]
# 90 days of hourly readings per sensor
DAYS = 90


def build_reference_frames():
    locations = pd.DataFrame(
        [(i + 1, f"{c[0]} Station", c[0], c[1], c[2]) for i, c in enumerate(CITIES)],
        columns=["location_id", "name", "city", "latitude", "longitude"],
    )
    sensors = []
    sid = 1
    for loc_id in locations.location_id:
        for stype, unit, _, _ in SENSOR_TYPES:
            sensors.append((sid, int(loc_id), stype, unit, "2024-01-01"))
            sid += 1
    sensors = pd.DataFrame(
        sensors,
        columns=["sensor_id", "location_id", "sensor_type", "unit", "installed_on"],
    )
    return locations, sensors


def build_readings(sensors: pd.DataFrame) -> pd.DataFrame:
    timestamps = pd.date_range("2024-04-01", periods=DAYS * 24, freq="h")
    means = {s: (m, sd) for s, _, m, sd in SENSOR_TYPES}
    hours = timestamps.hour.to_numpy()

    parts = []
    for _, s in sensors.iterrows():
        mean, sd = means[s.sensor_type]
        # daily seasonal cycle + noise
        season = np.sin((hours - 6) / 24 * 2 * np.pi) * (sd * 0.6)
        values = np.round(mean + season + RNG.normal(0, sd * 0.4, len(timestamps)), 2)
        if s.sensor_type == "humidity":
            values = values.clip(0, 100)
        if s.sensor_type == "pm25":
            values = values.clip(0, None)
        parts.append(pd.DataFrame({
            "sensor_id": s.sensor_id,
            "ts": timestamps.strftime("%Y-%m-%d %H:%M:%S"),
            "value": values,
        }))
    readings = pd.concat(parts, ignore_index=True)
    readings.insert(0, "reading_id", np.arange(1, len(readings) + 1))
    return readings


def load_sqlite(locations, sensors, readings) -> None:
    conn = sqlite3.connect(DB)
    with open(SCHEMA) as f:
        conn.executescript(f.read())

    locations.to_sql("locations", conn, if_exists="append", index=False)
    sensors.to_sql("sensors", conn, if_exists="append", index=False)

    # bulk insert the fact table in one transaction (fast, atomic)
    rows = list(readings.itertuples(index=False, name=None))
    conn.executemany(
        "INSERT INTO readings (reading_id, sensor_id, ts, value) VALUES (?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.execute("ANALYZE")
    conn.commit()
    conn.close()


def main() -> None:
    locations, sensors = build_reference_frames()
    readings = build_readings(sensors)

    load_sqlite(locations, sensors, readings)
    readings.to_parquet(PARQUET, index=False)

    print(f"Built {DB}")
    print(f"  locations: {len(locations)}  sensors: {len(sensors)}  "
          f"readings: {len(readings):,}")
    print(f"Exported {PARQUET}")


if __name__ == "__main__":
    main()
