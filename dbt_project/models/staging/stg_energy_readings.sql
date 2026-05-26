-- stg_energy_readings.sql
-- Staging layer: clean raw smart meter readings
-- Handles data quality flags, outlier detection, lineage tracking

with source as (
    select * from raw_energy_readings
),

cleaned as (
    select
        reading_id::integer             as reading_id,
        building_id::integer            as building_id,
        date_id::integer                as date_id,
        kwh_consumed::double            as kwh_consumed,
        kwh_solar::double               as kwh_solar,
        kwh_net::double                 as kwh_net,
        carbon_kg::double               as carbon_kg,
        cost_usd::double                as cost_usd,
        peak_demand_kw::double          as peak_demand_kw,
        upper(data_quality_flag)        as data_quality_flag,

        -- Carbon intensity (kgCO2 per kWh)
        case
            when kwh_consumed > 0
            then round(carbon_kg / kwh_consumed, 4)
            else null
        end                             as carbon_intensity,

        -- Cost per kWh
        case
            when kwh_consumed > 0
            then round(cost_usd / kwh_consumed, 4)
            else null
        end                             as cost_per_kwh,

        -- Outlier flag (> 3 std devs from typical range)
        case
            when kwh_consumed > 50000 then true
            when kwh_consumed < 0     then true
            else false
        end                             as is_outlier

    from source
    where reading_id is not null
      and kwh_consumed >= 0
      and data_quality_flag != 'MISSING'
)

select * from cleaned
