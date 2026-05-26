# property-config.md
# Populated in Stage 1.1.1 — lock data source before proceeding

## GA4 Property (Sensor)
- Property ID: [TBD — GA4 Demo Account]
- Measurement ID: [TBD — GA4 Demo Account]
- Data Source: [ ] Real Shopify Store  [x] GA4 Demo Account + Synthetic Shopify CSV  [ ] Synthetic Sandbox

## BigQuery
- GCP Project ID: [TBD — your own GCP project]
- Dataset Name: [TBD — if you copy data into your own dataset]
- Dataset Region: [TBD]
- Export Type:
  - GA4 Demo Source: Uses existing public export  
  - Query Location: `bigquery-public-data.ga4_obfuscated_sample_ecommerce`
  - Note: Public demo is **daily batch**; Mass Balance SQL mimics intraday streaming

## Confirmed Events
- [ ] purchase
- [ ] session_start
- [ ] page_view
- [ ] add_to_cart
- [ ] begin_checkout

## The Sensor (Frontend Events)
- Source: Google Merchandise Store (GA4 Demo Account)
- BigQuery Location: `bigquery-public-data.ga4_obfuscated_sample_ecommerce`
- Target Events: `purchase`, `session_start`
- Update Frequency: Daily batch (Mass Balance logic mimics intraday streaming)

## The Setpoint (Backend Truth)
- Source: Synthetic Shopify Orders CSV
- Script Path: `/scripts/generate_shopify_setpoint.py`
- Target Schema:
  - `order_id`
  - `total_price`
  - `financial_status`
  - `created_at_utc`
- Injected Failure Modes: Defined in `/docs/fmea.md`

## Notes
[Add any setup notes here]
