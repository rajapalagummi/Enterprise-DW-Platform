"""
Synthetic Data Generator — Urban Energy Consumption Data Warehouse
Generates realistic multi-source energy data across buildings, zones, and time
Simulates: smart meter readings, weather data, building registry, zone metadata
"""
import os
import duckdb
import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta
import random

fake = Faker()
np.random.seed(42)
random.seed(42)

DB_PATH = "data/energy_warehouse.duckdb"

BUILDING_TYPES = ["Residential High-Rise", "Commercial Office", "Retail", "Industrial", "Mixed-Use", "Government"]
ZONES = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
REGULATORY_AUTHORITIES = ["NYC-DOE", "ConEdison", "NYPA", "EPA-Region2"]

def generate_buildings(n=200):
    rows = []
    for i in range(1, n+1):
        btype = random.choice(BUILDING_TYPES)
        zone  = random.choice(ZONES)
        rows.append({
            "building_id":       i,
            "building_name":     f"{fake.last_name()} {random.choice(['Tower','Plaza','Center','Building','House'])}",
            "building_type":     btype,
            "zone":              zone,
            "address":           fake.street_address(),
            "year_built":        random.randint(1940, 2023),
            "total_sqft":        random.randint(5000, 500000),
            "num_floors":        random.randint(1, 60),
            "regulatory_authority": random.choice(REGULATORY_AUTHORITIES),
            "ll97_compliant":    random.choice([True, True, True, False]),
            "green_certified":   random.choice([True, False, False]),
            "created_at":        datetime(2020, 1, 1).isoformat(),
        })
    return pd.DataFrame(rows)

def generate_time_dim(start="2022-01-01", end="2024-12-31"):
    dates = pd.date_range(start, end, freq="D")
    rows = []
    for d in dates:
        rows.append({
            "date_id":       int(d.strftime("%Y%m%d")),
            "full_date":     d.date().isoformat(),
            "year":          d.year,
            "quarter":       d.quarter,
            "month":         d.month,
            "month_name":    d.strftime("%B"),
            "week":          d.isocalendar()[1],
            "day_of_week":   d.dayofweek,
            "day_name":      d.strftime("%A"),
            "is_weekend":    d.dayofweek >= 5,
            "is_holiday":    d.month == 12 and d.day == 25,
            "season":        ("Winter" if d.month in [12,1,2] else
                             "Spring" if d.month in [3,4,5] else
                             "Summer" if d.month in [6,7,8] else "Fall"),
        })
    return pd.DataFrame(rows)

def generate_weather(dates_df):
    rows = []
    for _, row in dates_df.iterrows():
        month = row["month"]
        base_temp = {1:-2,2:0,3:7,4:14,5:20,6:25,7:28,8:27,9:22,10:15,11:8,12:2}.get(month, 15)
        rows.append({
            "date_id":       row["date_id"],
            "avg_temp_c":    round(base_temp + np.random.normal(0, 4), 1),
            "max_temp_c":    round(base_temp + np.random.normal(4, 2), 1),
            "min_temp_c":    round(base_temp + np.random.normal(-4, 2), 1),
            "humidity_pct":  round(np.random.uniform(40, 90), 1),
            "wind_speed_kmh":round(np.random.exponential(15), 1),
            "precipitation_mm": round(max(0, np.random.exponential(3)), 1),
            "uv_index":      round(max(0, np.random.normal(4 if month in [6,7,8] else 2, 1)), 1),
            "cloud_cover_pct":round(np.random.uniform(10, 90), 1),
        })
    return pd.DataFrame(rows)

def generate_energy_readings(buildings_df, dates_df, n_per_building=3):
    """
    Fact table: daily energy readings per building
    Realistic consumption based on building type, size, weather
    """
    rows = []
    type_base = {
        "Residential High-Rise": 8.0,
        "Commercial Office":     15.0,
        "Retail":                12.0,
        "Industrial":            25.0,
        "Mixed-Use":             10.0,
        "Government":            9.0,
    }

    sample_dates = dates_df.sample(min(len(dates_df), 500), random_state=42)

    for _, bld in buildings_df.iterrows():
        base = type_base[bld["building_type"]]
        sqft_factor = bld["total_sqft"] / 50000

        for _, dt in sample_dates.iterrows():
            season_mult = {"Summer": 1.3, "Winter": 1.2, "Spring": 1.0, "Fall": 1.0}[dt["season"]]
            weekend_mult = 0.75 if dt["is_weekend"] and bld["building_type"] == "Commercial Office" else 1.0

            kwh = (base * sqft_factor * season_mult * weekend_mult
                   * np.random.lognormal(0, 0.15))

            carbon_kg = kwh * 0.233
            cost_usd  = kwh * random.uniform(0.12, 0.22)

            rows.append({
                "reading_id":      len(rows) + 1,
                "building_id":     bld["building_id"],
                "date_id":         dt["date_id"],
                "kwh_consumed":    round(kwh, 2),
                "kwh_solar":       round(kwh * random.uniform(0, 0.2) if bld["green_certified"] else 0, 2),
                "kwh_net":         round(kwh, 2),
                "carbon_kg":       round(carbon_kg, 2),
                "cost_usd":        round(cost_usd, 2),
                "peak_demand_kw":  round(kwh / 16 * random.uniform(1.2, 1.8), 2),
                "data_quality_flag": random.choices(["VALID","ESTIMATED","MISSING"],[0.92,0.06,0.02])[0],
            })

    return pd.DataFrame(rows)

def generate_ll97_compliance(buildings_df):
    """LL97 Local Law 97 compliance tracking — NYC carbon cap compliance"""
    rows = []
    for year in [2022, 2023, 2024]:
        for _, bld in buildings_df.iterrows():
            sqft = bld["total_sqft"]
            # Threshold: ~2.7 kgCO2/sqft for residential, 4.5 for commercial
            threshold_map = {
                "Residential High-Rise": 2.7,
                "Commercial Office":     4.5,
                "Retail":                3.9,
                "Industrial":            6.2,
                "Mixed-Use":             3.5,
                "Government":            3.0,
            }
            threshold = threshold_map[bld["building_type"]] * sqft
            actual    = threshold * random.uniform(0.6, 1.4)
            penalty   = max(0, (actual - threshold) * 0.000268)

            rows.append({
                "compliance_id":     len(rows) + 1,
                "building_id":       bld["building_id"],
                "year":              year,
                "carbon_limit_kg":   round(threshold, 2),
                "carbon_actual_kg":  round(actual, 2),
                "carbon_over_kg":    round(max(0, actual - threshold), 2),
                "penalty_usd":       round(penalty, 2),
                "compliant":         actual <= threshold,
                "submitted_date":    f"{year+1}-05-01",
            })
    return pd.DataFrame(rows)

def load_to_duckdb(db_path):
    os.makedirs("data", exist_ok=True)
    con = duckdb.connect(db_path)

    print("[DataGen] Generating buildings...")
    buildings = generate_buildings(200)

    print("[DataGen] Generating time dimension...")
    time_dim = generate_time_dim()

    print("[DataGen] Generating weather data...")
    weather = generate_weather(time_dim)

    print("[DataGen] Generating energy readings (fact table)...")
    readings = generate_energy_readings(buildings, time_dim)

    print("[DataGen] Generating LL97 compliance data...")
    compliance = generate_ll97_compliance(buildings)

    # Load raw/staging tables
    for name, df in [
        ("raw_buildings",   buildings),
        ("raw_time_dim",    time_dim),
        ("raw_weather",     weather),
        ("raw_energy_readings", readings),
        ("raw_ll97_compliance", compliance),
    ]:
        con.execute(f"DROP TABLE IF EXISTS {name}")
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM df")
        print(f"[DataGen] Loaded {name}: {len(df):,} rows")

    con.close()
    print(f"\n[DataGen] DuckDB warehouse ready: {db_path}")
    return {
        "buildings": len(buildings),
        "time_dim": len(time_dim),
        "weather": len(weather),
        "readings": len(readings),
        "compliance": len(compliance),
    }

if __name__ == "__main__":
    stats = load_to_duckdb(DB_PATH)
    print("\nDataset Summary:")
    for k, v in stats.items():
        print(f"  {k}: {v:,} records")
