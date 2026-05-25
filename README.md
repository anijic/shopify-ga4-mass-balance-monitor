# shopify-ga4-mass-balance-monitor

> **Business Question:** What is happening in my marketing funnel right now, and how do I reallocate budget based on near real-time GA4 event data?

---

## Project Overview

This project applies **Chemical Engineering Mass Balance principles** to GA4 marketing attribution. In a physical pipeline, mass in must equal mass out — any discrepancy signals a leak. Here, if Shopify orders do not reconcile with GA4 `purchase` events, there is a **data integrity leak** in the attribution pipeline.

**The monitor answers:** Where is the discrepancy, which channel is affected, and how much revenue is being mis-attributed?

---

## Stack

| Layer | Tool |
|---|---|
| Event Source | GA4 (Streaming Export → BigQuery intraday tables) |
| Ground Truth | Shopify Orders API / CSV export |
| Transformation | SQL (BigQuery) |
| Visualization | Looker Studio |
| QA Framework | FMEA (Failure Mode & Effects Analysis) |

---

## Phase Tracker

| Phase | Description | Status |
|---|---|---|
| **Phase 1** | Infrastructure & Data Source Setup | 🔄 In Progress |
| **Phase 2** | SQL Attribution Models (First-Touch, Last-Touch, Spend vs. Conversions) | ⬜ Not Started |
| **Phase 3** | Looker Studio Dashboard (4 panels + data integrity flag) | ⬜ Not Started |
| **Phase 4** | README, GitHub Pin & Portfolio Publish | ⬜ Not Started |

---

## Repository Structure

```
/sql          → Phase 2: Attribution SQL models + Mass Balance reconciliation query
/docs         → property-config.md | fmea.md | temporal-normalization.md
/scripts      → Utility scripts (e.g., synthetic data generator if sandbox)
/assets       → Dashboard screenshots, deliverable previews
README.md     → This file
```

---

## ChemE Engineering Lens

| Engineering Concept | Applied Here |
|---|---|
| **Mass Balance** | GA4 `purchase` count vs. Shopify `order_id` count — divergence > 2% = data integrity flag |
| **FMEA** | Pre-defined failure modes (iOS suppression, UTM stripping, cross-domain drops) documented before any code is written |
| **PID Control Loop** | Looker Studio dashboard detects deviation from expected attribution baseline and surfaces corrective alerts |
| **Redundancy Validation** | Critical KPIs (revenue, conversions) calculated via two independent methods — only published when both agree within 2% |

---

## Reference

- Research_Intel_Apr2026.md — Section 15 (Track B Project 4 Build Spec)
- ChemE_Transition_Strategy.md — Mass Balance ETL Integrity, FMEA Framework
