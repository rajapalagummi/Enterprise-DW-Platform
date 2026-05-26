-- metrics_energy_kpis.sql
-- Aggregated KPI metrics for executive dashboards
-- Powers Metabase dashboards and LookML measures
-- Grain: one row per building per month

with fact as (
    select * from {{ ref('fact_energy_consumption') }}
),

monthly_kpis as (
    select
        building_id,
        building_type,
        zone,
        regulatory_authority,
        year,
        month,
        season,

        -- Consumption KPIs
        sum(kwh_consumed)                               as total_kwh,
        sum(kwh_solar)                                  as total_solar_kwh,
        avg(kwh_consumed)                               as avg_daily_kwh,
        max(kwh_consumed)                               as peak_daily_kwh,
        min(kwh_consumed)                               as min_daily_kwh,

        -- Carbon KPIs
        sum(carbon_kg)                                  as total_carbon_kg,
        round(sum(carbon_kg) / 1000, 2)                 as total_carbon_tonnes,
        avg(carbon_intensity)                           as avg_carbon_intensity,

        -- Financial KPIs
        sum(cost_usd)                                   as total_cost_usd,
        avg(cost_per_kwh)                               as avg_cost_per_kwh,
        sum(daily_penalty_usd)                          as total_ll97_penalty_usd,

        -- Compliance KPIs
        count(case when ll97_violation_flag then 1 end) as days_in_violation,
        count(*)                                        as total_days,
        round(
            count(case when ll97_violation_flag then 1 end) * 100.0 / count(*), 2
        )                                               as violation_rate_pct,

        -- Efficiency KPIs
        round(sum(kwh_solar) / nullif(sum(kwh_consumed), 0) * 100, 2) as solar_pct,

        -- Rolling window (window functions for trend analysis)
        sum(sum(kwh_consumed)) over (
            partition by building_id
            order by year, month
            rows between 2 preceding and current row
        )                                               as rolling_3m_kwh,

        avg(avg(carbon_intensity)) over (
            partition by building_id
            order by year, month
            rows between 11 preceding and current row
        )                                               as rolling_12m_avg_carbon_intensity

    from fact
    group by 1,2,3,4,5,6,7
),

with_yoy as (
    select
        m.*,
        -- Year-over-year comparison using window function
        lag(total_kwh, 12) over (
            partition by building_id
            order by year, month
        )                                               as prev_year_kwh,

        round(
            (total_kwh - lag(total_kwh, 12) over (
                partition by building_id order by year, month
            )) / nullif(lag(total_kwh, 12) over (
                partition by building_id order by year, month
            ), 0) * 100, 2
        )                                               as yoy_kwh_change_pct

    from monthly_kpis m
)

select * from with_yoy
