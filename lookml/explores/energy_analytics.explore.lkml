# energy_analytics.explore.lkml
# LookML Explore: Energy Analytics
# Main explore joining buildings dimension to energy consumption facts
# Implements access controls, always_filter for performance, and label overrides

connection: "energy_warehouse"

# ── Include views ────────────────────────────────────────────────
include: "/views/buildings.view.lkml"
include: "/views/energy_consumption.view.lkml"

# ── Explore Definition ───────────────────────────────────────────
explore: energy_analytics {
  label:       "Energy Analytics"
  description: "NYC urban energy consumption, carbon emissions, LL97 compliance, and sustainability KPIs"
  group_label: "Urban Energy Intelligence"

  # Performance optimization: always filter on recent years
  always_filter: {
    filters: [energy_consumption.year: "2022,2023,2024"]
  }

  # Require at least one grouping dimension (prevents full table scans)
  required_access_grants: []

  join: buildings {
    type:         left_outer
    relationship: many_to_one
    sql_on:       ${energy_consumption.building_id} = ${buildings.building_id} ;;
    fields:       [buildings.building_name, buildings.building_type, buildings.zone,
                   buildings.size_category, buildings.ll97_compliant, buildings.green_certified,
                   buildings.regulatory_authority, buildings.total_sqft, buildings.count,
                   buildings.pct_ll97_compliant]
  }

  # ── Suggested Explores (self-service analytics shortcuts) ───────
  aggregate_table: rollup__energy_by_zone_month {
    query: {
      dimensions: [buildings.zone, energy_consumption.year, energy_consumption.month]
      measures:   [energy_consumption.total_kwh, energy_consumption.total_carbon_tonnes,
                   energy_consumption.total_cost_usd, energy_consumption.total_ll97_penalty]
    }
    materialization: {
      sql_trigger_value: SELECT MAX(date_id) FROM raw_energy_readings ;;
    }
  }
}

# ── Compliance Explore (restricted access) ───────────────────────
explore: ll97_compliance {
  label:       "LL97 Compliance Dashboard"
  description: "NYC Local Law 97 carbon cap compliance monitoring and penalty tracking"
  group_label: "Regulatory Compliance"
  hidden:      no

  from:        energy_analytics

  join: buildings {
    type:         left_outer
    relationship: many_to_one
    sql_on:       ${energy_consumption.building_id} = ${buildings.building_id} ;;
  }
}
