# temporal-normalization.md
# Completed in Stage 1.4 — prevents false-positive discrepancies in the Mass Balance

## The Problem
GA4 and Shopify use different timestamp formats and timezones.
Misalignment produces false-positive reconciliation failures.

## Timestamp Formats

| Source | Format | Timezone | Example |
|---|---|---|---|
| GA4 `event_timestamp` | Microseconds (INT64) | GA4 property local time | 1716667200000000 |
| Shopify `created_at` | ISO 8601 string | UTC | 2026-05-25T19:00:00Z |

## Conversion Logic (BigQuery SQL)

```sql
-- GA4: convert microseconds → UTC TIMESTAMP
TIMESTAMP_MICROS(event_timestamp) AS ga4_event_time_utc

-- Alternatively, if GA4 property is set to America/Toronto (EDT = UTC-4):
TIMESTAMP_ADD(TIMESTAMP_MICROS(event_timestamp), INTERVAL 4 HOUR) AS ga4_event_time_utc

-- Shopify: parse ISO 8601 string → TIMESTAMP
PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%SZ', created_at) AS shopify_order_time_utc
```

## Comparison Window
When joining GA4 purchases to Shopify orders, use a ±5-minute window to account for:
- Network latency between Shopify checkout completion and GA4 hit delivery
- Batch processing delays in BigQuery streaming ingestion

```sql
ABS(TIMESTAMP_DIFF(ga4_event_time_utc, shopify_order_time_utc, SECOND)) <= 300
```

## GA4 Property Timezone
- Property Timezone: [TBD — confirm in GA4 Admin → Property Settings]
- Document here once confirmed: _______________

## Status
- [ ] GA4 property timezone confirmed and documented above
- [ ] Conversion logic tested against at least 10 real or synthetic records
- [ ] temporal-normalization.md reviewed before Phase 2 begins
