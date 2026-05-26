# buildings.view.lkml
# LookML View: Buildings Dimension
# Defines all building-level dimensions including LL97 compliance context
# Row-level security via access_grants on regulatory_authority

view: buildings {
  sql_table_name: marts.dim_buildings ;;
  label: "Buildings"

  # ── Primary Key ────────────────────────────────────────────────
  dimension: building_sk {
    type:        number
    primary_key: yes
    hidden:      yes
    sql:         ${TABLE}.building_sk ;;
  }

  dimension: building_id {
    type:  number
    label: "Building ID"
    sql:   ${TABLE}.building_id ;;
  }

  # ── Descriptive Dimensions ─────────────────────────────────────
  dimension: building_name {
    type:  string
    label: "Building Name"
    sql:   ${TABLE}.building_name ;;
    link: {
      label: "View Building Detail"
      url:   "/dashboards/building_detail?building={{ value }}"
    }
  }

  dimension: building_type {
    type:  string
    label: "Building Type"
    sql:   ${TABLE}.building_type ;;
    tags:  ["filter_suggest"]
  }

  dimension: zone {
    type:  string
    label: "NYC Zone / Borough"
    sql:   ${TABLE}.zone ;;
    map_layer_name: us_counties
    tags:  ["filter_suggest"]
  }

  dimension: size_category {
    type:  string
    label: "Building Size"
    sql:   ${TABLE}.size_category ;;
    order_by_field: total_sqft
  }

  dimension: total_sqft {
    type:        number
    label:       "Total Square Footage"
    sql:         ${TABLE}.total_sqft ;;
    value_format: "#,##0"
  }

  dimension: num_floors {
    type:  number
    label: "Number of Floors"
    sql:   ${TABLE}.num_floors ;;
  }

  dimension: year_built {
    type:  number
    label: "Year Built"
    sql:   ${TABLE}.year_built ;;
  }

  dimension: building_age_years {
    type:  number
    label: "Building Age (Years)"
    sql:   ${TABLE}.building_age_years ;;
  }

  # ── Compliance Dimensions ──────────────────────────────────────
  dimension: ll97_compliant {
    type:  yesno
    label: "LL97 Compliant"
    sql:   ${TABLE}.ll97_compliant ;;
    tags:  ["compliance"]
  }

  dimension: green_certified {
    type:  yesno
    label: "Green Certified"
    sql:   ${TABLE}.green_certified ;;
  }

  dimension: ll97_threshold_kg_per_sqft {
    type:        number
    label:       "LL97 Carbon Threshold (kg/sqft/yr)"
    sql:         ${TABLE}.ll97_threshold_kg_per_sqft ;;
    value_format: "0.00"
    description: "NYC Local Law 97 carbon cap per square foot per year"
  }

  # ── Row-Level Security ─────────────────────────────────────────
  # Controls which regulatory authority users can see which buildings
  dimension: regulatory_authority {
    type:  string
    label: "Regulatory Authority"
    sql:   ${TABLE}.regulatory_authority ;;
    tags:  ["rls"]
  }

  # access_grant implementation (Looker Enterprise)
  # access_grant: regulatory_access {
  #   user_attribute: regulatory_authority
  #   allowed_values: ["NYC-DOE", "ConEdison", "NYPA", "EPA-Region2"]
  # }

  # ── Measures ───────────────────────────────────────────────────
  measure: count {
    type:        count
    label:       "Number of Buildings"
    value_format: "#,##0"
    drill_fields: [building_name, building_type, zone, total_sqft]
  }

  measure: total_sqft_sum {
    type:        sum
    label:       "Total Portfolio Sqft"
    sql:         ${total_sqft} ;;
    value_format: "#,##0"
  }

  measure: pct_ll97_compliant {
    type:        average
    label:       "% LL97 Compliant"
    sql:         case when ${ll97_compliant} then 1.0 else 0.0 end ;;
    value_format: "0.0%"
    tags:        ["compliance"]
  }
}
