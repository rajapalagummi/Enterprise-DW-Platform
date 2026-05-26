# energy_consumption.view.lkml
# LookML View: Energy Consumption Fact
# Core measures for energy, carbon, cost, and LL97 compliance KPIs
# Implements derived tables, running totals, and YoY comparisons

view: energy_consumption {
  sql_table_name: metrics.metrics_energy_kpis ;;
  label: "Energy Consumption"

  # ── Dimensions ─────────────────────────────────────────────────
  dimension: building_id {
    type:        number
    primary_key: yes
    hidden:      yes
    sql:         ${TABLE}.building_id ;;
  }

  dimension: year {
    type:  number
    label: "Year"
    sql:   ${TABLE}.year ;;
  }

  dimension: month {
    type:  number
    label: "Month"
    sql:   ${TABLE}.month ;;
    value_format: "00"
  }

  dimension: season {
    type:  string
    label: "Season"
    sql:   ${TABLE}.season ;;
    tags:  ["filter_suggest"]
  }

  dimension: zone {
    type:  string
    label: "Zone"
    sql:   ${TABLE}.zone ;;
  }

  dimension: building_type {
    type:  string
    label: "Building Type"
    sql:   ${TABLE}.building_type ;;
  }

  dimension: regulatory_authority {
    type:  string
    label: "Regulatory Authority"
    sql:   ${TABLE}.regulatory_authority ;;
    tags:  ["rls"]
  }

  # ── Energy Measures ────────────────────────────────────────────
  measure: total_kwh {
    type:        sum
    label:       "Total Energy (kWh)"
    sql:         ${TABLE}.total_kwh ;;
    value_format: "#,##0"
    description: "Total electricity consumption in kilowatt-hours"
    drill_fields: [buildings.building_name, total_kwh, total_carbon_tonnes]
  }

  measure: avg_daily_kwh {
    type:        average
    label:       "Avg Daily Consumption (kWh)"
    sql:         ${TABLE}.avg_daily_kwh ;;
    value_format: "#,##0.0"
  }

  measure: total_solar_kwh {
    type:        sum
    label:       "Solar Generation (kWh)"
    sql:         ${TABLE}.total_solar_kwh ;;
    value_format: "#,##0"
  }

  measure: solar_offset_pct {
    type:        average
    label:       "Solar Offset %"
    sql:         ${TABLE}.solar_pct ;;
    value_format: "0.0\"%\""
  }

  # ── Carbon Measures ────────────────────────────────────────────
  measure: total_carbon_tonnes {
    type:        sum
    label:       "Total Carbon Emissions (tonnes CO₂)"
    sql:         ${TABLE}.total_carbon_tonnes ;;
    value_format: "#,##0.0"
    tags:        ["sustainability", "compliance"]
    description: "Total CO₂ emissions in metric tonnes"
  }

  measure: avg_carbon_intensity {
    type:        average
    label:       "Avg Carbon Intensity (kgCO₂/kWh)"
    sql:         ${TABLE}.avg_carbon_intensity ;;
    value_format: "0.0000"
    tags:        ["sustainability"]
  }

  # ── Financial Measures ─────────────────────────────────────────
  measure: total_cost_usd {
    type:        sum
    label:       "Total Energy Cost ($)"
    sql:         ${TABLE}.total_cost_usd ;;
    value_format: "$#,##0"
  }

  measure: avg_cost_per_kwh {
    type:        average
    label:       "Avg Cost per kWh ($)"
    sql:         ${TABLE}.avg_cost_per_kwh ;;
    value_format: "$0.0000"
  }

  # ── LL97 Compliance Measures ───────────────────────────────────
  measure: total_ll97_penalty {
    type:        sum
    label:       "Total LL97 Penalty Exposure ($)"
    sql:         ${TABLE}.total_ll97_penalty_usd ;;
    value_format: "$#,##0"
    tags:        ["compliance", "legal"]
    description: "Estimated fines under NYC Local Law 97 at $268/tonne CO₂ over cap"
  }

  measure: avg_violation_rate {
    type:        average
    label:       "LL97 Violation Rate (%)"
    sql:         ${TABLE}.violation_rate_pct ;;
    value_format: "0.0\"%\""
    tags:        ["compliance"]
  }

  measure: total_violation_days {
    type:        sum
    label:       "Total Days in LL97 Violation"
    sql:         ${TABLE}.days_in_violation ;;
    value_format: "#,##0"
    tags:        ["compliance"]
  }

  # ── Trend Measures (Window Functions) ─────────────────────────
  measure: rolling_3m_kwh {
    type:        sum
    label:       "Rolling 3-Month kWh"
    sql:         ${TABLE}.rolling_3m_kwh ;;
    value_format: "#,##0"
    description: "3-month rolling sum of energy consumption"
  }

  measure: yoy_kwh_change_pct {
    type:        average
    label:       "YoY Energy Change (%)"
    sql:         ${TABLE}.yoy_kwh_change_pct ;;
    value_format: "+0.0\"%\";-0.0\"%\""
    description: "Year-over-year percentage change in energy consumption"
  }
}
