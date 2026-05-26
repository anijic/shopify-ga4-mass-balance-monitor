# fmea.md — Failure Mode & Effects Analysis
# Completed in Stage 1.2 before any tracking code is written
# Rule: divergence >2% between GA4 purchase count and Shopify order count = data integrity flag

## Known Failure Modes

| # | Failure Mode | Cause | Effect on Attribution | Severity (H/M/L) | Detection Method | Status |
|---|---|---|---|---|---|---|
| 1 | iOS ad-blocker suppression | Safari ITP / ad blockers strip GA4 tag | Undercounts sessions + purchases from iOS users | H | Compare GA4 iOS sessions vs. Shopify iOS orders | [ ] Investigated |
| 2 | Cross-domain session drops | GA4 linker not configured for cross-domain | Session breaks at checkout subdomain; channel resets to Direct | H | Check % of purchase events with source = (direct) | [ ] Investigated |
| 3 | Server-side timeout | GA4 hit does not reach collection endpoint | Purchase event never fires; conversion lost | H | GA4 purchase count < Shopify order count | [ ] Investigated |
| 4 | UTM stripping at redirect | Shopify redirects strip query params | UTM source/medium lost; traffic misattributed to Direct | M | % of sessions with NULL utm_source on purchase events | [ ] Investigated |
| 5 | Duplicate purchase event fires | Tag fires on page re-load or back-button | GA4 purchase count > Shopify order count | M | Deduplicate on transaction_id | [ ] Investigated |
| 6 | [Add more as discovered] | | | | | |

## Redundancy Validation Method

**Critical KPI: Purchase / Conversion Count**
- Method A: GA4 `purchase` event count (deduplicated by transaction_id)
- Method B: Shopify `order_id` count (financial_status = 'paid')
- Threshold: If |Method A - Method B| / Method B > 2% → FLAG as data integrity issue. Do not publish until resolved.

## Status
- [ ] All failure modes documented
- [ ] Redundancy method defined and agreed
- [ ] fmea.md reviewed before Phase 2 begins
