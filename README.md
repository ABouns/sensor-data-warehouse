# Sensor Data Warehouse — storage & retrieval

A **data-storage / database-design** project. It models high-volume IoT sensor
readings in a normalised SQLite store and demonstrates *why* common storage decisions
matter: schema design, bulk loading, indexing, and choosing a storage format.

Dataset: 4 locations × 3 sensor types × 90 days of hourly readings ≈ **26,000 measurements**.

## Schema

Defined in [`schema.sql`](schema.sql) — reference tables kept separate from the narrow,
high-volume fact table:

```
locations (location_id PK, name, city, lat, lon)
sensors   (sensor_id PK, location_id FK, sensor_type, unit, installed_on)
readings  (reading_id PK, sensor_id FK, ts, value)        <- fact table, ~26k rows
          INDEX (sensor_id, ts)   -- the dominant access pattern
```

## What it demonstrates

- **Normalisation** — no repeated city names / units per reading; FK joins instead.
- **Efficient bulk loading** — `executemany()` inside a single transaction.
- **Indexing impact** — the same range query timed with vs without the composite
  index (full scan → index range scan, measured speed-up).
- **Time-series queries** — daily aggregation / rollups in SQL.
- **Storage-format trade-offs** — the same table as CSV vs SQLite vs **Parquet**,
  compared on file size and full-scan read time.

## What's inside

```
sensor-data-warehouse/
├── schema.sql               # the DDL (tables, FKs, index)
├── src/
│   └── build_store.py       # generate data + bulk-load + Parquet export
├── data/
│   ├── sensors.db           # SQLite store (generated)
│   └── readings.parquet     # columnar export (generated)
├── notebooks/
│   └── storage_demo.ipynb   # schema, indexing benchmark, format comparison
└── requirements.txt
```

## Run it

```bash
pip install -r requirements.txt
python src/build_store.py                  # build the store from schema.sql
jupyter notebook notebooks/storage_demo.ipynb
```

## Key takeaway

SQLite gives you indexed point/range queries for operational access; Parquet is much
smaller and faster for full-table analytical scans. The right answer is workload-driven
— often **both** (an operational DB plus a columnar export for analytics).

---
Part of my [data & ML portfolio](https://github.com/ABouns).
