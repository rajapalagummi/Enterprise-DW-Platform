# executive_sustainability.dashboard.lookml
# LookML Dashboard: Executive Sustainability Report
# Renders in Looker as a full interactive dashboard
# Equivalent built in Metabase for local demo

- dashboard: executive_sustainability
  title: "NYC Urban Energy Intelligence — Executive Dashboard"
  layout: newspaper
  preferred_viewer: dashboards-next

  filters:
    - name: year
      title: "Year"
      type: field_filter
      default_value: "2024"
      explore: energy_analytics
      field: energy_consumption.year
      allow_multiple_values: false
      required: false

    - name: zone
      title: "NYC Zone / Borough"
      type: field_filter
      default_value: ""
      explore: energy_analytics
      field: buildings.zone
      allow_multiple_values: true
      required: false

    - name: building_type
      title: "Building Type"
      type: field_filter
      default_value: ""
      explore: energy_analytics
      field: buildings.building_type
      allow_multiple_values: true
      required: false

  elements:
    - title: "Total Energy Consumed (kWh)"
      name: kpi_total_kwh
      model: energy_dw
      explore: energy_analytics
      type: single_value
      fields: [energy_consumption.total_kwh]
      listen:
        year: energy_consumption.year
        zone: buildings.zone
      row: 0
      col: 0
      width: 6
      height: 4

    - title: "Total Carbon Emissions (tonnes CO₂)"
      name: kpi_carbon
      model: energy_dw
      explore: energy_analytics
      type: single_value
      fields: [energy_consumption.total_carbon_tonnes]
      listen:
        year: energy_consumption.year
        zone: buildings.zone
      row: 0
      col: 6
      width: 6
      height: 4

    - title: "Total LL97 Penalty Exposure"
      name: kpi_penalty
      model: energy_dw
      explore: energy_analytics
      type: single_value
      fields: [energy_consumption.total_ll97_penalty]
      listen:
        year: energy_consumption.year
        zone: buildings.zone
      row: 0
      col: 12
      width: 6
      height: 4

    - title: "% Buildings LL97 Compliant"
      name: kpi_compliance
      model: energy_dw
      explore: energy_analytics
      type: single_value
      fields: [buildings.pct_ll97_compliant]
      listen:
        zone: buildings.zone
      row: 0
      col: 18
      width: 6
      height: 4

    - title: "Monthly Energy Trend by Zone"
      name: trend_zone
      model: energy_dw
      explore: energy_analytics
      type: looker_line
      fields: [energy_consumption.year, energy_consumption.month,
               buildings.zone, energy_consumption.total_kwh]
      pivots: [buildings.zone]
      listen:
        year: energy_consumption.year
      row: 4
      col: 0
      width: 12
      height: 8

    - title: "Carbon Emissions by Building Type"
      name: carbon_by_type
      model: energy_dw
      explore: energy_analytics
      type: looker_bar
      fields: [buildings.building_type, energy_consumption.total_carbon_tonnes]
      sorts: [energy_consumption.total_carbon_tonnes desc]
      listen:
        year: energy_consumption.year
        zone: buildings.zone
      row: 4
      col: 12
      width: 12
      height: 8

    - title: "LL97 Violation Rate by Zone"
      name: violation_map
      model: energy_dw
      explore: energy_analytics
      type: looker_column
      fields: [buildings.zone, energy_consumption.avg_violation_rate]
      sorts: [energy_consumption.avg_violation_rate desc]
      listen:
        year: energy_consumption.year
      row: 12
      col: 0
      width: 12
      height: 8

    - title: "Top 10 Buildings — Penalty Exposure"
      name: top_penalty_buildings
      model: energy_dw
      explore: energy_analytics
      type: looker_bar
      fields: [buildings.building_name, energy_consumption.total_ll97_penalty]
      sorts: [energy_consumption.total_ll97_penalty desc]
      limit: 10
      listen:
        year: energy_consumption.year
        zone: buildings.zone
      row: 12
      col: 12
      width: 12
      height: 8
