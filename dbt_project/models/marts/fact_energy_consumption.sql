-- fact_energy_consumption.sql
-- Core fact table: daily energy consumption per building
-- Star schema center — joins to dim_buildings, dim_date, dim_weather
-- Grain: one row per building per day

with readings as (
    select * from {{ ref('stg_energy_readings') }}
    where is_outlier = false
      and data_quality_flag = 'VALID'
),

buildings as (
    select building_id, building_type, zone, total_sqft,
           ll97_threshold_kg_per_sqft, regulatory_authority
    from {{ ref('dim_buildings') }}
),

weather as (
    select * from raw_weather
),

time_dim as (
    select * from raw_time_dim
),

joined as (
    select
        -- Keys
        r.reading_id,
        r.building_id,
        r.date_id,

        -- Measures
        r.kwh_consumed,
        r.kwh_solar,
        r.kwh_net,
        r.carbon_kg,
        r.cost_usd,
        r.peak_demand_kw,
        r.carbon_intensity,
        r.cost_per_kwh,

        -- LL97 compliance measure
        round(r.carbon_kg / nullif(b.total_sqft, 0), 6)    as carbon_kg_per_sqft,
        b.ll97_threshold_kg_per_sqft                        as ll97_threshold,
        case
            when (r.carbon_kg / nullif(b.total_sqft, 0)) > b.ll97_threshold_kg_per_sqft
            then true else false
        end                                                 as ll97_violation_flag,

        -- Penalty estimate (daily pro-rated)
        case
            when (r.carbon_kg / nullif(b.total_sqft, 0)) > b.ll97_threshold_kg_per_sqft
            then round(
                ((r.carbon_kg / nullif(b.total_sqft, 0)) - b.ll97_threshold_kg_per_sqft)
                * b.total_sqft * 0.000268 / 365, 2
            )
            else 0.0
        end                                                 as daily_penalty_usd,

        -- Context
        b.building_type,
        b.zone,
        b.total_sqft,
        b.regulatory_authority,
        t.year,
        t.quarter,
        t.month,
        t.season,
        t.is_weekend,
        w.avg_temp_c,
        w.uv_index,
        w.precipitation_mm

    from readings r
    left join buildings b  on r.building_id = b.building_id
    left join time_dim  t  on r.date_id = t.date_id
    left join weather   w  on r.date_id = w.date_id
)

select * from joined
