# Failure Mode and Effects Analysis (FMEA)

**System:** Shopify-to-GA4 Mass Balance Pipeline  
**Project:** `shopify-ga4-mass-balance-monitor`  
**Objective:** Identify, quantify, and engineer detection mechanisms for revenue-attribution leaks.

---

## Engineering Redundancy Rule

No critical KPI, including Total Revenue and Total Conversions, will be reported from the GA4 Sensor without first passing a dual-validation check against the Shopify Setpoint.

> **Rule:** Divergence greater than 2% between GA4 `purchase` event count and Shopify `order_id` count triggers a data-integrity alert. Do not publish the affected KPI until the discrepancy is investigated.

---

## Failure Mode Register

### FM-01: Client-Side Tracker Suppression (iOS / ITP / Ad Blockers)

- **Description:** A user completes a purchase. Shopify records the revenue, but the user's browser blocks the GA4 tracking script. The conversion is not recorded by GA4.
- **Severity:** 9 — Direct loss of ROAS visibility
- **Probability:** 7 — Increasing with iOS privacy controls and ad-blocker adoption
- **Effect:** GA4 purchase count is lower than the Shopify order count. Revenue is under-reported in attribution dashboards.
- **Detection Mechanism:** A `FULL OUTER JOIN` reveals a Shopify `order_id` with no corresponding GA4 `transaction_id`.
- **SQL Signature:**
  ```sql
  WHERE ga4.transaction_id IS NULL
    AND shopify.order_id IS NOT NULL
  ```
- **Status:** [x] Investigated
- **Architectural Response:** Addressed by the first-party Server-Side Tagging architecture, which routes collection through `collect.aniji.ca` before forwarding events to the server container.
- **Validation Status:** Demonstrated on representative public GA4 sample data and synthetic Shopify data. A post-cutover measurement confirming a reduction in the suppression rate has not yet been completed.

---

### FM-02: Cross-Domain Session Drop-off (The UTM Strip)

- **Description:** A user clicks an ad, lands on the store with UTMs captured, but transitions to `checkout.shopify.com` without proper GA4 linker parameters. The purchase fires in GA4 but is attributed to `(direct) / (none)`.
- **Severity:** 8 — Revenue is counted, but channel attribution is destroyed
- **Probability:** 6 — Common in multi-site and Shopify-hosted checkout architectures
- **Effect:** Mass balance on total revenue passes. Mass balance on channel revenue fails. Paid campaigns appear under-performing while Direct appears inflated.
- **Detection Mechanism:** Revenue reconciles correctly at the total level but channel attribution breaks. Flag purchases where the source is `(direct)` but the referrer points to a known paid channel.
- **SQL Signature:**
  ```sql
  WHERE ga4.event_name = 'purchase'
    AND ga4.session_source = '(direct)'
    AND ga4.page_referrer LIKE '%google.com%'
  ```
- **Status:** [ ] Investigated

---

### FM-03: The Phantom Purchase (Cancelled / Voided Orders)

- **Description:** A user completes checkout. GA4 fires the `purchase` event immediately. Minutes later, Shopify voids the order because of fraud detection or customer cancellation.
- **Severity:** 8 — Over-reporting revenue; inflates perceived ad performance
- **Probability:** 3 — Low frequency, high financial and reporting impact
- **Effect:** GA4 shows valid revenue while the Shopify Setpoint shows a non-revenue status. ROAS is overstated.
- **Detection Mechanism:** Join the GA4 transaction ID to the Shopify order ID and flag non-paid financial statuses.
- **SQL Signature:**
  ```sql
  WHERE ga4.transaction_id = shopify.order_id
    AND shopify.financial_status IN ('voided', 'refunded', 'cancelled')
  ```
- **Status:** [ ] Investigated

---

### FM-04: UTM Stripping at Redirect

- **Description:** Shopify or a third-party application redirects the user mid-funnel and strips UTM query parameters before GA4 captures them.
- **Severity:** 7 — Channel attribution is corrupted at source
- **Probability:** 6 — Common when URL redirects are not configured to preserve parameters
- **Effect:** `utm_source`, `utm_medium`, and `utm_campaign` arrive as `NULL` or `(not set)` on purchase events.
- **Detection Mechanism:** Flag purchase events where UTM parameters are `NULL` or `(not set)`.
- **SQL Signature:**
  ```sql
  WHERE ga4.event_name = 'purchase'
    AND (utm_source IS NULL OR utm_source = '(not set)')
  ```
- **Status:** [ ] Investigated

---

### FM-05: Duplicate Purchase Event Fire

- **Description:** The GA4 `purchase` tag fires more than once for the same order because of a page reload, back-button navigation, or tag misconfiguration.
- **Severity:** 6 — Revenue is double-counted; conversion rate is artificially inflated
- **Probability:** 4 — Occurs in GTM implementations without transaction-ID deduplication
- **Effect:** GA4 purchase count is higher than the Shopify order count. Revenue is over-reported.
- **Detection Mechanism:** Deduplicate GA4 purchase events on `transaction_id`. Flag any `transaction_id` appearing more than once.
- **SQL Signature:**
  ```sql
  SELECT transaction_id, COUNT(*) AS fire_count
  FROM ga4_purchases
  GROUP BY transaction_id
  HAVING COUNT(*) > 1
  ```
- **Status:** [ ] Investigated

---

## Summary Table

| ID | Failure Mode | Severity | Probability | RPN (S × P) | SQL Phase |
|---|---|---:|---:|---:|---|
| FM-01 | Client-Side Tracker Suppression | 9 | 7 | 63 | Phase 2 |
| FM-02 | Cross-Domain UTM Strip | 8 | 6 | 48 | Phase 2 |
| FM-03 | Phantom Purchase (Voided Orders) | 8 | 3 | 24 | Phase 2 |
| FM-04 | UTM Stripping at Redirect | 7 | 6 | 42 | Phase 2 |
| FM-05 | Duplicate Purchase Event Fire | 6 | 4 | 24 | Phase 2 |

> **RPN = Risk Priority Number (Severity × Probability).** A higher RPN indicates a higher priority for detection and remediation. FM-01 is the highest-risk failure mode in this register.

---

## Current Register Status

- [x] All five failure modes documented
- [x] Engineering redundancy rule defined
- [x] FM-01 investigated and assigned a first-party SST architectural response
- [ ] Post-cutover FM-01 reduction measured through a second validation cycle
- [ ] FM-02 through FM-05 individually investigated and closed
- [x] `fmea.md` reviewed and aligned with the current project architecture
