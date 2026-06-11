# Enterprise Data Warehouse & Governance Platform
## dbt + LookML + DuckDB + Metabase | Urban Energy Analytics

---

## Overview

Every large organization managing physical assets faces the same problem: data about those assets lives in siloed source systems — building registries, smart meters, weather APIs, compliance databases — and nobody has a single, trusted, queryable view of it all.

This project builds a production-grade data warehouse for NYC urban energy consumption data, implementing the full analytics engineering stack: raw ingestion → dbt staging → dimensional star schema → LookML semantic layer → live Metabase dashboards. The domain is urban building energy and LL97 compliance (NYC's Local Law 97 carbon cap), but the architecture directly applies to any organization that needs trusted, governed, self-service analytics.

Every transformation is documented in dbt with schema tests. Every measure is defined in LookML with access controls. Every KPI is backed by traceable SQL with CTEs, window functions, and YoY comparisons.

---

## Project Goals

- Build a star schema data warehouse with proper fact and dimension tables from raw multi-source data
- Implement dbt models across three layers: staging (clean), marts (dimensional), metrics (aggregated KPIs)
- Write LookML views and explores that define a semantic layer with row-level security and self-serve analytics
- Apply dbt schema tests for data quality: unique keys, not null, accepted values, referential integrity
- Generate executive-ready dashboards from the semantic layer using Metabase (live, free, open-source)
- Document data lineage end-to-end from raw sources through to dashboard measures

---

## Architecture

```
Raw Sources (DuckDB)
    raw_buildings          ← 200 NYC buildings
    raw_energy_readings    ← 100,000 daily smart meter readings
    raw_weather            ← 1,096 daily weather records
    raw_time_dim           ← Calendar dimension (2022–2024)
    raw_ll97_compliance    ← 600 LL97 annual submissions
         │
         ▼
dbt Staging Layer (views)
    stg_buildings          ← Type casting, DQ flags, size categories
    stg_energy_readings    ← Outlier detection, carbon intensity, cost/kWh
         │
         ▼
dbt Marts Layer (tables — star schema)
    dim_buildings          ← Dimension: LL97 thresholds, RLS tags, surrogate key
    fact_energy_consumption← Fact: daily consumption, carbon, penalty, weather join
         │
         ▼
dbt Metrics Layer (tables)
    metrics_energy_kpis    ← Monthly KPIs with CTEs, window functions, YoY
         │
         ▼
LookML Semantic Layer
    buildings.view.lkml         ← Dimensions, measures, drill-through, RLS
    energy_consumption.view.lkml← Energy/carbon/cost/compliance measures
    energy_analytics.explore.lkml← Join logic, access control, aggregate awareness
    executive_sustainability.dashboard.lookml
         │
         ▼
Metabase Live Dashboards
    Executive Summary  ← Energy, carbon, cost, LL97 KPIs
    Compliance Report  ← Violation rates, penalty exposure, zone breakdown
    Building Drilldown ← Per-building trend analysis
```

---

## Key Technical Implementations

### 1. dbt Dimensional Modeling — Star Schema

Fact table grain: one row per building per day

```sql
-- fact_energy_consumption.sql
select
    r.reading_id, r.building_id, r.date_id,
    r.kwh_consumed, r.carbon_kg, r.cost_usd,

    -- LL97 compliance calculation
    round(r.carbon_kg / nullif(b.total_sqft, 0), 6)  as carbon_kg_per_sqft,
    b.ll97_threshold_kg_per_sqft                      as ll97_threshold,
    case
        when (r.carbon_kg / nullif(b.total_sqft, 0)) > b.ll97_threshold_kg_per_sqft
        then true else false
    end                                               as ll97_violation_flag,

    -- Daily penalty estimate
    case
        when ll97_violation_flag
        then round(excess_carbon * 0.000268 / 365, 2)
        else 0.0
    end                                               as daily_penalty_usd
from readings r
left join dim_buildings b on r.building_id = b.building_id
```

### 2. SQL Window Functions in dbt Metrics

CTEs + rolling windows + YoY in the metrics layer:

```sql
-- metrics_energy_kpis.sql
monthly_kpis as (
    select
        building_id, year, month,
        sum(kwh_consumed)       as total_kwh,
        sum(carbon_kg) / 1000   as total_carbon_tonnes,

        -- Rolling 3-month window
        sum(sum(kwh_consumed)) over (
            partition by building_id
            order by year, month
            rows between 2 preceding and current row
        )                       as rolling_3m_kwh,

        -- YoY % change
        round(
            (total_kwh - lag(total_kwh, 12) over (
                partition by building_id order by year, month
            )) / nullif(lag(total_kwh, 12) over (...), 0) * 100, 2
        )                       as yoy_kwh_change_pct
    from fact
    group by 1, 2, 3
)
```

### 3. LookML Semantic Layer with Row-Level Security

LookML defines the business logic once — every dashboard, every user, every team uses the same definitions:

```lookml
# energy_consumption.view.lkml
measure: total_ll97_penalty {
  type:        sum
  label:       "Total LL97 Penalty Exposure ($)"
  sql:         ${TABLE}.total_ll97_penalty_usd ;;
  value_format: "$#,##0"
  tags:        ["compliance", "legal"]
  description: "Estimated fines at $268/tonne CO₂ over NYC LL97 cap"
  drill_fields: [buildings.building_name, total_kwh, total_carbon_tonnes]
}

# Row-level security (Looker Enterprise)
dimension: regulatory_authority {
  type: string
  sql:  ${TABLE}.regulatory_authority ;;
  tags: ["rls"]
  # access_grant controls which authority sees which buildings
}
```

### 4. dbt Schema Tests — Data Quality Enforcement

12 tests defined in schema.yml:

```yaml
- name: dim_buildings
  columns:
    - name: building_sk
      tests:
        - unique
        - not_null
    - name: building_type
      tests:
        - accepted_values:
            values: ['RESIDENTIAL HIGH-RISE','COMMERCIAL OFFICE','RETAIL'...]
    - name: rls_authority_tag
      tests:
        - not_null
```

45 tests passed across all 5 models.

### 5. Data Governance Documentation

Every model is documented with:
- Column descriptions in schema.yml
- Data lineage JSON tracking raw → staging → mart → metric → semantic layer
- DQ report: 93.8% valid readings, outlier detection, completeness tracking
- Audit trail via dbt run artifacts

---

## Tools and Technologies

| Layer | Technology | Purpose |
|---|---|---|
| Storage | DuckDB | Embedded analytics database — no server needed |
| Transformation | dbt-duckdb | SQL transformations with testing and lineage |
| Semantic Layer | LookML | Looker view/explore/dashboard definitions |
| Live Dashboards | Metabase | Open-source BI — connects directly to DuckDB |
| Data Generation | Python + Faker | Realistic synthetic NYC energy data |
| Visualization | Matplotlib | Executive summary outputs |

---

## Key Metrics

- **102,992** total records across 5 source tables
- **200** NYC buildings across 5 boroughs and 6 building types
- **100,000** daily smart meter readings (3 years, 2022–2024)
- **5 dbt models**: 2 staging views + 2 mart tables + 1 metrics table
- **45 data quality tests** passed (unique, not_null, accepted_values, referential integrity)
- **93.8%** valid reading rate with outlier detection and DQ flagging
- **7,200 rows** in the monthly KPI metrics table with rolling windows and YoY
- **3 LookML files**: 2 views + 1 explore with access controls + 1 dashboard definition
- **4 outputs**: executive dashboard, data lineage map, KPI CSV, DQ report

---

## Generated Outputs

```
outputs/
├── executive_dashboard.png     ← Hero image: KPIs, trends, LL97 compliance
├── energy_kpis.csv             ← 7,200 monthly KPI rows for Metabase import
├── data_lineage.json           ← End-to-end lineage documentation
└── data_quality_report.json    ← DQ metrics and governance controls
```

---

## How to Run

```bash
# 1. Unzip and navigate
cd ~/Desktop/Projects/enterprise-dw-platform

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run full pipeline (data gen + dbt + outputs)
python3 main.py
```

---

## Metabase Live Dashboard Setup

```bash
# 1. Run Metabase in Docker (no Java needed)
docker run -d -p 3000:3000 --name metabase metabase/metabase

# 2. Open http://localhost:3000 and complete setup

# 3. Install DuckDB driver for Metabase:
#    Settings → Admin → Databases → Add Database
#    Download driver from: https://github.com/AlexR2D2/metabase_duckdb_driver/releases
#    Copy to: ~/.metabase/plugins/

# 4. Add database:
#    Type: DuckDB
#    Database file: //absolute/path/to/data/energy_warehouse.duckdb

# 5. Browse tables in main_metrics, main_marts schemas
#    Build dashboards using energy_kpis.csv as reference for available fields
```

---

## LookML Reference Implementation

The `lookml/` folder contains a complete Looker implementation ready to deploy to any Looker instance:

```
lookml/
├── views/
│   ├── buildings.view.lkml          ← Building dimensions + RLS
│   └── energy_consumption.view.lkml ← Energy/carbon/cost/LL97 measures
├── explores/
│   └── energy_analytics.explore.lkml← Join logic + access grants
└── dashboards/
    └── executive_sustainability.dashboard.lookml
```

To deploy: connect to a Looker instance, point to this folder as the LookML project, and configure the DuckDB connection string.

---

## Real-World Applications

**Retail Analytics (Nordstrom, RTR context)** — Replace energy readings with sales transactions, buildings with stores, zones with regions. The same star schema, the same LookML semantic layer, the same dbt test framework. The architecture is domain-agnostic.

**Regulatory Compliance** — LL97 compliance tracking directly mirrors how financial institutions track regulatory capital requirements. Row-level security mirrors how banks restrict data access by regulatory authority.

**Self-Service Analytics** — LookML enables non-technical stakeholders to build their own reports without writing SQL. The semantic layer guarantees everyone uses the same KPI definitions.

---

*Built by Raja Palagummi | rajapalagummi.com | github.com/rajapalagummi*
