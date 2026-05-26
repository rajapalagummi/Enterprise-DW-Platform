-- stg_buildings.sql
-- Staging layer: clean and standardize raw building registry data
-- Applies data quality checks and type casting

with source as (
    select * from raw_buildings
),

cleaned as (
    select
        building_id::integer                        as building_id,
        trim(building_name)                         as building_name,
        upper(trim(building_type))                  as building_type,
        upper(trim(zone))                           as zone,
        trim(address)                               as address,
        year_built::integer                         as year_built,
        total_sqft::integer                         as total_sqft,
        num_floors::integer                         as num_floors,
        upper(trim(regulatory_authority))           as regulatory_authority,
        ll97_compliant::boolean                     as ll97_compliant,
        green_certified::boolean                    as green_certified,
        created_at::timestamp                       as created_at,

        -- Derived fields
        current_date - year_built::integer          as building_age_years,
        case
            when total_sqft < 25000  then 'Small'
            when total_sqft < 100000 then 'Medium'
            when total_sqft < 250000 then 'Large'
            else 'Enterprise'
        end                                         as size_category,

        -- Data quality flag
        case
            when building_name is null then 'INVALID'
            when total_sqft <= 0      then 'INVALID'
            when year_built < 1800    then 'INVALID'
            else 'VALID'
        end                                         as dq_status

    from source
    where building_id is not null
)

select * from cleaned
