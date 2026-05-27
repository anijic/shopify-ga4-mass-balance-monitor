#!/usr/bin/env python3
"""
generate_shopify_setpoint.py
Track B, Project 4 - shopify-ga4-mass-balance-monitor

CSV INPUT SCHEMA (ga4_transactions_jan2021.csv):
    transaction_id      : GA4 join key
    ga4_revenue         : INT, 608/904 rows are NULL (by design - obfuscated dataset)
    event_date          : YYYYMMDD
    event_timestamp_utc : UTC timestamp string

FMEA FAILURE MODES INJECTED:
    FM-01: 15% ghost orders - Shopify recorded sale, GA4 missed it (ad-blocker)
    FM-03: 5%  voided orders - GA4 fired, Shopify later cancelled

OUTPUT (shopify_orders_setpoint.csv):
    order_id         : matches GA4 transaction_id (or GHOST_XXXX for FM-01)
    total_price      : revenue in USD - real where available, synthetic where NULL
    financial_status : paid / voided / refunded
    created_at_utc   : UTC timestamp
    has_ga4_match    : True/False - critical flag for Phase 2 FULL OUTER JOIN
"""

import pandas as pd
import numpy as np
import os
import random

# ── CONFIGURATION ──────────────────────────────────────────
INPUT_CSV             = "ga4_transactions_jan2021.csv"
OUTPUT_CSV            = "shopify_orders_setpoint.csv"
FM01_SUPPRESSION_RATE = 0.15
FM03_PHANTOM_RATE     = 0.05
RANDOM_SEED           = 42
# ───────────────────────────────────────────────────────────


def load_ga4_seed(filepath):
    """
    BLOCK 1 - LOAD GA4 SEED DATA
    Reads the CSV, drops null transaction_ids, parses timestamps.
    """
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()
    df = df.dropna(subset=["transaction_id"])
    df["transaction_id"] = df["transaction_id"].astype(str).str.strip()
    df["event_timestamp_utc"] = pd.to_datetime(
        df["event_timestamp_utc"], utc=True, errors="coerce"
    )
    print(f"[LOAD]   GA4 seed rows loaded:           {len(df)}")
    print(f"[LOAD]   Columns confirmed:              {list(df.columns)}")
    return df


def build_matched_orders(df, fm03_rate, seed):
    """
    BLOCK 2 - BUILD MATCHED ORDERS
    Maps each GA4 transaction_id to a Shopify order_id 1:1.
    Revenue: uses real ga4_revenue where available, synthetic where NULL.
    Injects FM-03 (voided/refunded) at 5%.
    """
    rng = np.random.default_rng(seed + 1)
    n   = len(df)

    # Revenue safeguard: real values where present, synthetic where NULL
    ga4_rev       = pd.to_numeric(df["ga4_revenue"], errors="coerce")
    synthetic_rev = rng.uniform(25.0, 250.0, size=n).round(2)
    revenue       = ga4_rev.where(ga4_rev.notna() & (ga4_rev > 0), synthetic_rev)

    # FM-03: mark ~5% of matched orders as voided or refunded
    n_phantom      = int(n * fm03_rate)
    phantom_idx    = rng.choice(n, size=n_phantom, replace=False)
    fin_status     = np.full(n, "paid", dtype=object)
    fin_status[phantom_idx] = rng.choice(["voided", "refunded"], size=n_phantom)

    # Shopify timestamp = GA4 timestamp + small delay (0-300 sec)
    delay          = pd.to_timedelta(rng.integers(0, 300, size=n), unit="s")
    shopify_ts     = df["event_timestamp_utc"].values + delay

    matched_df = pd.DataFrame({
        "order_id":         df["transaction_id"].values,
        "total_price":      revenue.values,
        "financial_status": fin_status,
        "created_at_utc":   pd.to_datetime(shopify_ts, utc=True),
        "has_ga4_match":    True
    })

    n_voided = (fin_status != "paid").sum()
    print(f"[FM-03]  Phantom/voided orders injected: {n_voided}  ({fm03_rate*100:.0f}% phantom rate)")
    return matched_df


def inject_fm01_ghost_orders(matched_df, rate, seed):
    """
    BLOCK 3 - INJECT FM-01: GHOST ORDERS
    Creates Shopify orders with NO matching GA4 transaction_id.
    IDs are prefixed GHOST_ so they are unambiguous in Phase 2 SQL.
    has_ga4_match = False flags these for FULL OUTER JOIN verification.
    """
    rng     = np.random.default_rng(seed)
    n_ghost = int(len(matched_df) * rate / (1 - rate))

    ghost_ids = [f"GHOST_{i:04d}" for i in range(n_ghost)]

    real_dates      = matched_df["created_at_utc"].dropna().values
    ghost_ts        = pd.to_datetime(
        rng.choice(real_dates, size=n_ghost), utc=True
    ) + pd.to_timedelta(rng.integers(0, 3600, size=n_ghost), unit="s")

    ghost_df = pd.DataFrame({
        "order_id":         ghost_ids,
        "total_price":      rng.uniform(15.0, 250.0, size=n_ghost).round(2),
        "financial_status": "paid",
        "created_at_utc":   ghost_ts,
        "has_ga4_match":    False
    })
    print(f"[FM-01]  Ghost orders injected:          {n_ghost}  ({rate*100:.0f}% suppression rate)")
    return ghost_df


def generate_setpoint(input_csv, output_csv):
    """
    BLOCK 4 - MASTER ORCHESTRATOR
    Runs all blocks, combines output, saves CSV, prints Mass Balance Summary.
    """
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    print("=" * 60)
    print("  Shopify Setpoint Generator - Track B Project 4")
    print("=" * 60)

    ga4_df     = load_ga4_seed(input_csv)
    matched_df = build_matched_orders(ga4_df, FM03_PHANTOM_RATE, RANDOM_SEED)
    ghost_df   = inject_fm01_ghost_orders(matched_df, FM01_SUPPRESSION_RATE, RANDOM_SEED)

    setpoint_df = pd.concat([matched_df, ghost_df], ignore_index=True)
    setpoint_df = setpoint_df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)
    setpoint_df.to_csv(output_csv, index=False)

    total   = len(setpoint_df)
    matched = int(setpoint_df["has_ga4_match"].sum())
    ghost   = int((~setpoint_df["has_ga4_match"]).sum())
    voided  = int(setpoint_df["financial_status"].isin(["voided","refunded"]).sum())
    paid    = int((setpoint_df["financial_status"] == "paid").sum())
    nullrev = int(setpoint_df["total_price"].isna().sum())

    print()
    print("=" * 60)
    print("  MASS BALANCE SUMMARY (Engineering QA Check)")
    print("=" * 60)
    print(f"  Total Shopify orders generated:  {total}")
    print(f"  Orders with GA4 match:           {matched}  (Setpoint + Sensor)")
    print(f"  Ghost orders (FM-01):            {ghost}  (Shopify only, no GA4 match)")
    print(f"  Voided/refunded orders (FM-03):  {voided}  (GA4 fired, Shopify cancelled)")
    print(f"  Paid orders:                     {paid}")
    print(f"  Null revenue rows:               {nullrev}  (must be 0)")
    print(f"  FM-01 rate (actual):             {ghost/total*100:.1f}%  (target ~15%)")
    print(f"  FM-03 rate (actual):             {voided/total*100:.1f}%  (target ~5%)")
    print()
    print(f"  Output saved to:                 {output_csv}")
    print("=" * 60)


if __name__ == "__main__":
    script_dir  = os.path.dirname(os.path.abspath(__file__))
    input_path  = os.path.join(script_dir, INPUT_CSV)
    output_path = os.path.join(script_dir, OUTPUT_CSV)
    generate_setpoint(input_path, output_path)
