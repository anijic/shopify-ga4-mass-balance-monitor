-- ============================================================
-- Track B, Project 4 | GA4 ↔ Shopify Mass Balance Monitor
-- Author: Charles Aniji | github.com/anijic
-- Stack: BigQuery (GoogleSQL), Python, Looker Studio
-- Project: portfolio-project-412322
-- ============================================================

-- STEP 1: GA4 Purchases Staging Table
-- Creates: mass_balance_monitor.ga4_purchases_jan2021
-- Source:  bigquery-public-data.ga4_obfuscated_sample_ecommerce
-- Rows expected: 904

CREATE OR REPLACE TABLE `portfolio-project-412322.mass_balance_monitor.ga4_purchases_jan2021` AS
WITH raw AS (
  SELECT
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'transaction_id') AS transaction_id,
    (SELECT value.int_value   FROM UNNEST(event_params) WHERE key = 'value')           AS ga4_revenue,
    event_date,
    TIMESTAMP_MICROS(event_timestamp) AS event_timestamp_utc,
    traffic_source.source  AS session_source,
    traffic_source.medium  AS session_medium,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'utm_source')   AS utm_source,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'utm_medium')   AS utm_medium,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'utm_campaign') AS utm_campaign
  FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
  WHERE _TABLE_SUFFIX BETWEEN '20210101' AND '20210131'
    AND event_name = 'purchase'
)
SELECT
  transaction_id, ga4_revenue, event_date, event_timestamp_utc,
  session_source, session_medium, utm_source, utm_medium, utm_campaign
FROM raw
WHERE transaction_id IS NOT NULL;


-- ============================================================
-- STEP 2: Mass Balance Reactor Table (FULL OUTER JOIN)
-- Creates: mass_balance_monitor.ga4_shopify_mass_balance_jan2021
-- Setpoint: mass_balance_monitor.shopify_orders_setpoint
-- Sensor:   mass_balance_monitor.ga4_purchases_jan2021

CREATE OR REPLACE TABLE `portfolio-project-412322.mass_balance_monitor.ga4_shopify_mass_balance_jan2021` AS
WITH ga4 AS (
  SELECT transaction_id, ga4_revenue, event_timestamp_utc, event_date,
         session_source, session_medium, utm_source, utm_medium, utm_campaign
  FROM `portfolio-project-412322.mass_balance_monitor.ga4_purchases_jan2021`
),
shopify AS (
  SELECT order_id, total_price, financial_status, created_at_utc, has_ga4_match
  FROM `portfolio-project-412322.mass_balance_monitor.shopify_orders_setpoint`
)
SELECT
  ga4.transaction_id      AS ga4_transaction_id,
  shopify.order_id        AS shopify_order_id,
  ga4.event_timestamp_utc,
  shopify.created_at_utc  AS shopify_created_at_utc,
  ga4.ga4_revenue,
  shopify.total_price     AS shopify_total_price,
  ga4.session_source, ga4.session_medium,
  ga4.utm_source, ga4.utm_medium, ga4.utm_campaign,
  shopify.financial_status,
  shopify.has_ga4_match,
  CASE
    WHEN ga4.transaction_id IS NOT NULL AND shopify.order_id IS NOT NULL THEN 'both'
    WHEN ga4.transaction_id IS NOT NULL AND shopify.order_id IS NULL     THEN 'ga4_only'
    WHEN ga4.transaction_id IS NULL     AND shopify.order_id IS NOT NULL THEN 'shopify_only'
    ELSE 'neither'
  END AS join_bucket
FROM ga4
FULL OUTER JOIN shopify ON ga4.transaction_id = shopify.order_id;


-- ============================================================
-- STEP 3a: FMEA Mass Balance Reconciliation View
-- Creates: mass_balance_monitor.vw_mass_balance_reconciliation

CREATE OR REPLACE VIEW `portfolio-project-412322.mass_balance_monitor.vw_mass_balance_reconciliation` AS
SELECT
  ga4_transaction_id, shopify_order_id,
  event_timestamp_utc  AS ga4_event_timestamp_utc,
  shopify_created_at_utc AS shopify_timestamp,
  ga4_revenue, shopify_total_price AS shopify_revenue,
  ROUND(COALESCE(shopify_total_price, 0) - COALESCE(ga4_revenue, 0), 2) AS revenue_delta,
  financial_status, has_ga4_match, join_bucket,
  session_source, session_medium, utm_source, utm_medium, utm_campaign,
  CASE
    WHEN join_bucket = 'shopify_only'
      THEN 'FM-01: Tracker Suppressed — Shopify Only'
    WHEN join_bucket = 'both'
     AND financial_status IN ('voided', 'refunded', 'cancelled')
      THEN 'FM-03: Phantom Purchase — Voided/Refunded'
    WHEN join_bucket = 'ga4_only'
      THEN 'FM-05: Sensor Ghost — GA4 Only'
    ELSE 'Verified Match'
  END AS integrity_status
FROM `portfolio-project-412322.mass_balance_monitor.ga4_shopify_mass_balance_jan2021`;


-- ============================================================
-- STEP 3b: Channel Attribution Health View
-- Creates: mass_balance_monitor.vw_channel_attribution_health
-- Isolates 4.95% Phantom ROAS contamination in Direct channel

CREATE OR REPLACE VIEW `portfolio-project-412322.mass_balance_monitor.vw_channel_attribution_health` AS
SELECT
  COALESCE(utm_source, 'direct')    AS source,
  COALESCE(utm_medium, 'none')      AS medium,
  COALESCE(utm_campaign, 'not set') AS campaign,
  COUNT(CASE WHEN ga4_revenue IS NOT NULL THEN 1 END)              AS ga4_reported_conversions,
  ROUND(SUM(ga4_revenue), 2)                                       AS ga4_reported_revenue,
  COUNT(CASE WHEN integrity_status = 'Verified Match' THEN 1 END)  AS true_conversions,
  ROUND(SUM(CASE WHEN integrity_status = 'FM-03: Phantom Purchase — Voided/Refunded'
                 THEN ga4_revenue ELSE 0 END), 2)                  AS phantom_revenue_leak,
  ROUND(
    SUM(CASE WHEN integrity_status = 'FM-03: Phantom Purchase — Voided/Refunded'
             THEN ga4_revenue ELSE 0 END)
    / NULLIF(SUM(ga4_revenue), 0) * 100, 2)                        AS over_attribution_error_pct
FROM `portfolio-project-412322.mass_balance_monitor.vw_mass_balance_reconciliation`
WHERE integrity_status != 'FM-01: Tracker Suppressed — Shopify Only'
GROUP BY source, medium, campaign
HAVING ga4_reported_revenue > 0
ORDER BY phantom_revenue_leak DESC;
