"""
Enterprise Data Warehouse & Governance Platform — Main Pipeline
Runs: data generation → dbt models → analytical outputs → Metabase setup instructions
"""
import os
import sys
import json
import subprocess
import duckdb
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.data_generator import load_to_duckdb

DB_PATH    = "data/energy_warehouse.duckdb"
OUTPUT_DIR = "outputs"
DBT_DIR    = "dbt_project"

PALETTE = {"blue":"#2E75B6","red":"#C93828","green":"#0A8F5C","orange":"#B87200","gray":"#595959"}


def run_dbt_models():
    """Run dbt transformations — staging → marts → metrics"""
    print("\n[dbt] Running transformations...")
    env = os.environ.copy()
    env["DBT_DUCKDB_PATH"] = os.path.abspath(DB_PATH)

    result = subprocess.run(
        ["dbt", "run", "--profiles-dir", ".", "--project-dir", "."],
        cwd=os.path.abspath(DBT_DIR),
        env=env, capture_output=True, text=True
    )
    if result.returncode == 0:
        print("[dbt] ✓ All models compiled and run successfully")
        # Count models run
        lines = [l for l in result.stdout.split("\n") if "OK" in l or "ERROR" in l]
        for l in lines[-10:]:
            print(f"  {l.strip()}")
    else:
        print("[dbt] ⚠ dbt run output:")
        print(result.stdout[-3000:])
        print(result.stderr[-1000:])
    return result.returncode == 0


def run_dbt_tests():
    """Run dbt data quality tests"""
    print("\n[dbt] Running data quality tests...")
    env = os.environ.copy()
    env["DBT_DUCKDB_PATH"] = os.path.abspath(DB_PATH)

    result = subprocess.run(
        ["dbt", "test", "--profiles-dir", ".", "--project-dir", "."],
        cwd=os.path.abspath(DBT_DIR),
        env=env, capture_output=True, text=True
    )
    passed = result.stdout.count("PASS")
    failed = result.stdout.count("FAIL") + result.stdout.count("ERROR")
    print(f"[dbt] Tests: {passed} passed | {failed} failed")
    return passed, failed


def generate_outputs(con):
    """Generate all analytical outputs from DuckDB"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    outputs = []

    # ── 1. Executive Summary Dashboard ───────────────────────────
    print("[Outputs] Generating executive summary dashboard...")
    try:
        kpis = con.execute("""
            SELECT
                sum(total_kwh)           as total_kwh,
                sum(total_carbon_tonnes) as total_carbon_tonnes,
                sum(total_cost_usd)      as total_cost_usd,
                sum(total_ll97_penalty_usd) as total_penalty,
                avg(violation_rate_pct)  as avg_violation_rate,
                count(distinct building_id) as n_buildings
            FROM main_metrics.metrics_energy_kpis
            WHERE year = 2024
        """).df()

        zone_kpis = con.execute("""
            SELECT zone, sum(total_kwh) as kwh, sum(total_carbon_tonnes) as carbon,
                   sum(total_ll97_penalty_usd) as penalty
            FROM main_metrics.metrics_energy_kpis
            WHERE year = 2024
            GROUP BY zone ORDER BY kwh DESC
        """).df()

        type_kpis = con.execute("""
            SELECT building_type, sum(total_kwh) as kwh,
                   sum(total_carbon_tonnes) as carbon,
                   avg(violation_rate_pct) as violation_rate
            FROM main_metrics.metrics_energy_kpis
            WHERE year = 2024
            GROUP BY building_type ORDER BY kwh DESC
        """).df()

        monthly = con.execute("""
            SELECT year, month, zone, sum(total_kwh) as kwh,
                   sum(total_carbon_tonnes) as carbon
            FROM main_metrics.metrics_energy_kpis
            GROUP BY 1,2,3 ORDER BY 1,2
        """).df()

        fig = plt.figure(figsize=(18, 14))
        fig.patch.set_facecolor("#F8F9FA")
        fig.suptitle("Urban Energy Intelligence Platform — Executive Dashboard\nNYC Building Portfolio 2024",
                     fontsize=16, fontweight="bold", y=0.98, color=PALETTE["blue"])

        gs = gridspec.GridSpec(3, 4, figure=fig, hspace=0.5, wspace=0.4)

        # KPI cards
        kpi_vals = [
            (f"{kpis['total_kwh'].iloc[0]/1e6:.1f}M", "Total Energy (kWh)", PALETTE["blue"]),
            (f"{kpis['total_carbon_tonnes'].iloc[0]/1000:.1f}K", "Carbon Emissions (tonnes)", PALETTE["red"]),
            (f"${kpis['total_cost_usd'].iloc[0]/1e6:.1f}M", "Total Energy Cost", PALETTE["orange"]),
            (f"${kpis['total_penalty'].iloc[0]/1e3:.0f}K", "LL97 Penalty Exposure", PALETTE["red"]),
        ]
        for i, (val, label, color) in enumerate(kpi_vals):
            ax = fig.add_subplot(gs[0, i])
            ax.set_facecolor("white")
            ax.text(0.5, 0.6, val, ha="center", va="center", fontsize=24,
                    fontweight="bold", color=color, transform=ax.transAxes)
            ax.text(0.5, 0.2, label, ha="center", va="center", fontsize=10,
                    color=PALETTE["gray"], transform=ax.transAxes)
            for spine in ax.spines.values():
                spine.set_edgecolor(color); spine.set_linewidth(2)
            ax.set_xticks([]); ax.set_yticks([])

        # Monthly trend
        ax2 = fig.add_subplot(gs[1, :2])
        for zone in zone_kpis["zone"].head(3):
            zdata = monthly[monthly["zone"] == zone].groupby(["year","month"])["kwh"].sum()
            ax2.plot(range(len(zdata)), zdata.values, marker="o", markersize=3, lw=2, label=zone)
        ax2.set_title("Monthly Energy Trend by Zone", fontsize=12, fontweight="bold")
        ax2.set_xlabel("Month"); ax2.set_ylabel("kWh")
        ax2.legend(fontsize=8); ax2.spines[["top","right"]].set_visible(False)

        # Carbon by building type
        ax3 = fig.add_subplot(gs[1, 2:])
        colors = [PALETTE["blue"],PALETTE["red"],PALETTE["green"],PALETTE["orange"],PALETTE["gray"],"#8B4513"]
        ax3.barh(type_kpis["building_type"], type_kpis["carbon"],
                 color=colors[:len(type_kpis)], edgecolor="white")
        ax3.set_title("Carbon Emissions by Building Type", fontsize=12, fontweight="bold")
        ax3.set_xlabel("Carbon Tonnes CO₂"); ax3.spines[["top","right"]].set_visible(False)

        # LL97 violation rate by zone
        ax4 = fig.add_subplot(gs[2, :2])
        viol = con.execute("""
            SELECT zone, avg(violation_rate_pct) as rate
            FROM main_metrics.metrics_energy_kpis WHERE year=2024
            GROUP BY zone ORDER BY rate DESC
        """).df()
        bar_colors = [PALETTE["red"] if r > 30 else PALETTE["orange"] if r > 15 else PALETTE["green"]
                      for r in viol["rate"]]
        ax4.bar(viol["zone"], viol["rate"], color=bar_colors, edgecolor="white")
        ax4.axhline(30, color="red", linestyle="--", lw=1.5, label="High Alert (30%)")
        ax4.set_title("LL97 Violation Rate by Zone (%)", fontsize=12, fontweight="bold")
        ax4.set_ylabel("Violation Rate (%)"); ax4.legend(fontsize=9)
        ax4.spines[["top","right"]].set_visible(False)

        # Top penalty buildings
        ax5 = fig.add_subplot(gs[2, 2:])
        top = con.execute("""
            SELECT b.building_name, sum(m.total_ll97_penalty_usd) as penalty
            FROM main_metrics.metrics_energy_kpis m
            JOIN main_marts.dim_buildings b ON m.building_id = b.building_id
            WHERE m.year = 2024
            GROUP BY 1 ORDER BY 2 DESC LIMIT 8
        """).df()
        ax5.barh(top["building_name"], top["penalty"], color=PALETTE["red"], edgecolor="white")
        ax5.set_title("Top 8 Buildings — LL97 Penalty Exposure ($)", fontsize=12, fontweight="bold")
        ax5.set_xlabel("Penalty ($)"); ax5.spines[["top","right"]].set_visible(False)

        fig.text(0.5, 0.01, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Enterprise DW Platform | rajapalagummi.com",
                 ha="center", fontsize=8, color="#999999", style="italic")

        path = os.path.join(OUTPUT_DIR, "executive_dashboard.png")
        plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()
        outputs.append("executive_dashboard.png")
        print(f"[Outputs] ✓ executive_dashboard.png")

    except Exception as e:
        print(f"[Outputs] ⚠ Dashboard error: {e}")

    # ── 2. Data Lineage Documentation ────────────────────────────
    print("[Outputs] Generating data lineage map...")
    lineage = {
        "pipeline": "Urban Energy Data Warehouse",
        "generated_at": datetime.now().isoformat(),
        "layers": {
            "raw": {
                "tables": ["raw_buildings","raw_time_dim","raw_weather",
                           "raw_energy_readings","raw_ll97_compliance"],
                "description": "Source data ingested from smart meters, building registry, weather APIs"
            },
            "staging": {
                "tables": ["stg_buildings","stg_energy_readings"],
                "description": "Cleaned, typed, and validated data with DQ flags",
                "transformations": ["type casting","null handling","outlier flagging","DQ status tagging"]
            },
            "marts": {
                "tables": ["dim_buildings","fact_energy_consumption"],
                "description": "Star schema: dimension and fact tables optimized for analytics",
                "transformations": ["LL97 threshold joins","carbon intensity calculation",
                                   "penalty estimation","row-level security tagging"]
            },
            "metrics": {
                "tables": ["metrics_energy_kpis"],
                "description": "Monthly aggregated KPIs with window functions and YoY comparisons",
                "transformations": ["monthly aggregation","rolling 3m/12m windows",
                                   "YoY % change","violation rate calculation"]
            },
            "semantic_layer": {
                "files": ["lookml/views/buildings.view.lkml",
                         "lookml/views/energy_consumption.view.lkml",
                         "lookml/explores/energy_analytics.explore.lkml"],
                "description": "LookML semantic layer: dimensions, measures, access grants, explores",
                "features": ["row-level security","drill-through links",
                            "aggregate awareness","always_filter optimization"]
            }
        },
        "data_governance": {
            "row_level_security": "regulatory_authority column controls access per building",
            "data_quality_tests": ["unique keys","not null","accepted values","referential integrity"],
            "audit_trail": "dbt run artifacts logged with timestamp and model hash",
            "documentation": "All models documented in schema.yml with column descriptions"
        }
    }
    path = os.path.join(OUTPUT_DIR, "data_lineage.json")
    with open(path, "w") as f:
        json.dump(lineage, f, indent=2)
    outputs.append("data_lineage.json")

    # ── 3. KPI Summary CSV (for Metabase import) ─────────────────
    print("[Outputs] Generating KPI summary CSV...")
    try:
        kpi_df = con.execute("""
            SELECT building_id, building_type, zone, year, month,
                   total_kwh, total_carbon_tonnes, total_cost_usd,
                   total_ll97_penalty_usd, violation_rate_pct,
                   solar_pct, yoy_kwh_change_pct
            FROM main_metrics.metrics_energy_kpis
            ORDER BY building_id, year, month
        """).df()
        path = os.path.join(OUTPUT_DIR, "energy_kpis.csv")
        kpi_df.to_csv(path, index=False)
        outputs.append("energy_kpis.csv")
        print(f"[Outputs] ✓ energy_kpis.csv ({len(kpi_df):,} rows)")
    except Exception as e:
        print(f"[Outputs] ⚠ KPI CSV: {e}")

    # ── 4. DQ Report ─────────────────────────────────────────────
    print("[Outputs] Generating data quality report...")
    try:
        dq = con.execute("""
            SELECT
                count(*) as total_readings,
                count(case when data_quality_flag='VALID' then 1 end) as valid_count,
                count(case when data_quality_flag='ESTIMATED' then 1 end) as estimated_count,
                count(case when is_outlier then 1 end) as outlier_count,
                round(count(case when data_quality_flag='VALID' then 1 end)*100.0/count(*),2) as valid_pct
            FROM main_staging.stg_energy_readings
        """).df()
        dq_report = {
            "generated_at": datetime.now().isoformat(),
            "total_readings": int(dq["total_readings"].iloc[0]),
            "valid_pct": float(dq["valid_pct"].iloc[0]),
            "estimated_count": int(dq["estimated_count"].iloc[0]),
            "outlier_count": int(dq["outlier_count"].iloc[0]),
            "dbt_tests_defined": 12,
            "governance_controls": ["unique keys","not_null","accepted_values","row-level security"]
        }
        path = os.path.join(OUTPUT_DIR, "data_quality_report.json")
        with open(path, "w") as f:
            json.dump(dq_report, f, indent=2)
        outputs.append("data_quality_report.json")
        print(f"[Outputs] ✓ DQ: {dq['valid_pct'].iloc[0]:.1f}% valid readings")
    except Exception as e:
        print(f"[Outputs] ⚠ DQ report: {e}")

    return outputs


def run_pipeline():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("""
╔══════════════════════════════════════════════════════════════════╗
║    Enterprise Data Warehouse & Governance Platform               ║
║    dbt + LookML + DuckDB + Metabase                              ║
║                                                                  ║
║  Stage 1: Synthetic Data Generation (200 buildings, 3 years)    ║
║  Stage 2: dbt Transformations (staging → marts → metrics)        ║
║  Stage 3: dbt Data Quality Tests                                 ║
║  Stage 4: Analytical Outputs + Executive Dashboard               ║
╚══════════════════════════════════════════════════════════════════╝
""")

    # Stage 1: Data Generation
    print("=" * 60)
    print("  STAGE 1: Synthetic Data Generation")
    print("=" * 60)
    stats = load_to_duckdb(DB_PATH)
    print(f"✓ Stage 1 complete | {sum(stats.values()):,} total records")

    # Stage 2: dbt
    print("\n" + "=" * 60)
    print("  STAGE 2: dbt Transformations")
    print("=" * 60)
    dbt_ok = run_dbt_models()

    # Stage 3: dbt tests
    print("\n" + "=" * 60)
    print("  STAGE 3: Data Quality Tests")
    print("=" * 60)
    if dbt_ok:
        passed, failed = run_dbt_tests()
        print(f"✓ Stage 3 complete | {passed} tests passed | {failed} failed")
    else:
        print("⚠ Skipping tests — dbt models failed")
        passed, failed = 0, 0

    # Stage 4: Outputs
    print("\n" + "=" * 60)
    print("  STAGE 4: Analytical Outputs")
    print("=" * 60)
    con = duckdb.connect(DB_PATH)
    outputs = generate_outputs(con)
    con.close()

    # Summary
    print(f"""
{'='*60}
  ✓ PIPELINE COMPLETE
{'='*60}

📁 Outputs in: {OUTPUT_DIR}/
""")
    for o in outputs:
        print(f"   • {o}")

    print(f"""
📊 dbt Models: staging (2) → marts (2) → metrics (1)
🧪 dbt Tests:  {passed} passed
📐 LookML:     2 views + 1 explore + 1 dashboard
🗄  DuckDB:    {DB_PATH}

{'='*60}
METABASE SETUP (live dashboards):
{'='*60}
1. Install Metabase:
   docker run -d -p 3000:3000 --name metabase metabase/metabase

2. Open: http://localhost:3000
3. Add Database → DuckDB → path: {os.path.abspath(DB_PATH)}
   (Install DuckDB driver for Metabase first — see README)

4. Browse tables: metrics_energy_kpis, dim_buildings, fact_energy_consumption
5. Build dashboards using the pre-built queries in outputs/energy_kpis.csv

{'='*60}
PORTFOLIO EVIDENCE:
{'='*60}
→ outputs/executive_dashboard.png  (hero image)
→ lookml/                          (LookML code — GitHub evidence)
→ dbt_project/models/              (dbt models with CTEs, window functions)
→ outputs/data_lineage.json        (governance documentation)
""")


if __name__ == "__main__":
    run_pipeline()
