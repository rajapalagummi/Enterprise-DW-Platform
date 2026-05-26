-- dim_buildings.sql
-- Dimension table: buildings with full descriptive context
-- Star schema dimension — joins to fact_energy_consumption
-- Implements row-level security zone tagging for regulatory access control

with stg as (
    select * from {{ ref('stg_buildings') }}
    where dq_status = 'VALID'
),

enriched as (
    select
        building_id,
        building_name,
        building_type,
        zone,
        address,
        year_built,
        total_sqft,
        num_floors,
        regulatory_authority,
        ll97_compliant,
        green_certified,
        building_age_years,
        size_category,
        created_at,

        -- LL97 threshold by building type (kgCO2/sqft/year)
        -- Source: NYC Local Law 97 penalty schedule
        case building_type
            when 'RESIDENTIAL HIGH-RISE' then 2.7
            when 'COMMERCIAL OFFICE'     then 4.5
            when 'RETAIL'                then 3.9
            when 'INDUSTRIAL'            then 6.2
            when 'MIXED-USE'             then 3.5
            when 'GOVERNMENT'            then 3.0
            else 3.5
        end                             as ll97_threshold_kg_per_sqft,

        -- Row-level security tag: which regulatory authority can view this building
        -- Used in LookML access_grants and Metabase row policies
        regulatory_authority            as rls_authority_tag,

        -- Surrogate key for SCD Type 1
        row_number() over (order by building_id) as building_sk

    from stg
)

select * from enriched
