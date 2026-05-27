#!/usr/bin/env python3
"""
generate_shopify_setpoint.py
Track B, Project 4 — shopify-ga4-mass-balance-monitor

PURPOSE:
    Reads the 904 valid GA4 transaction_ids extracted from the GA4 Sensor
    (bigquery-public-data.ga4_obfuscated_sample_ecommerce) and generates a
    synthetic Shopify orders CSV (The Setpoint) with controlled FMEA failure
    modes injected at realistic rates.

FMEA FAILURE MODES INJECTED:
    FM-01: ~15% of Shopify orders have NO matching GA4 transaction_id
           (simulates iOS/ad-blocker suppression — Shopify recorded it, GA4 missed it)
    FM-03: ~5% of matched orders get financial_status = 'voided'
           (simulates phantom purchase — GA4 fired, Shopify later cancelled)
    FM-05: Already visible in GA4 raw data (duplicate transaction_id fires)
           Handled in Phase 2 SQL, not injected here.

OUTPUT:
    shopify_orders_setpoint.csv

SCHEMA:
    order_id         — matches GA4 transaction_id where a match exists
    total_price      — synthetic revenue in USD (realistic Shopify range)
    financial_status — 'paid', 'voided', or 'refunded'
    created_at_utc   — UTC timestamp aligned to GA4 event_timestamp_utc
    has_ga4_match    — True/False flag (used to verify FM-01 injection)
"""

import pandas as pd
import numpy as np
import os
from datetime import timedelta
import random

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
# Adjust this path if your CSV is not in the same folder as this script
INPUT_CSV  = "ga4_transactions_jan2021.csv"
OUTPUT_CSV = "shopify_orders_setpoint.csv"

# FMEA injection rates (match fmea.md)
FM01_SUPPRESSION_RATE = 0.15   # 15% of Shopify orders have no GA4 match
FM03_PHANTOM_RATE     = 0.05   # 5%  of matched orders are voided/refunded

RANDOM_SEED = 42               # Makes results reproducible across runs
# ──────────────────────────────────────────────────────────────────────────────

def load_ga4_seed(filepath):
    """
    BLOCK 1 — LOAD GA4 SEED DATA
    Reads the exported GA4 CSV. Drops rows where transaction_id is null
    (those cannot be joined to Shopify and are not useful as a seed).
    """
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()
    df = df.dropna(subset=["transaction_id"])
    df["transaction_id"] = df["transaction_id"].astype(str).str.strip()
    df["event_timestamp_utc"] = pd.to_datetime(
        df["event_timestamp_utc"], utc=True, errors="coerce"
    )
    print(f"[LOAD]   GA4 seed rows loaded:         {len(df)}")
    return df

def inject_fm01_ghost_orders(df, rate, seed):
    """
    BLOCK 2 — INJECT FM-01: GHOST ORDERS (Shopify recorded, GA4 missed)
    Creates synthetic Shopify orders that have NO matching GA4 transaction_id.
    These simulate purchases where the GA4 tag was blocked by iOS/ad-blocker.
    In Phase 2 SQL, these will surface as:
        WHERE ga4.transaction_id IS NULL AND shopify.order_id IS NOT NULL
    """
    rng = np.random.default_rng(seed)
    n_ghost = int(len(df) * rate / (1 - rate))   # maintain realistic ratio

    # Generate synthetic order IDs that cannot match any real GA4 transaction_id
    ghost_ids = [f"GHOST_{i:04d}" for i in range(n_ghost)]

    # Anchor ghost order timestamps to real dates in the dataset
    real_dates = df["event_timestamp_utc"].dropna().values
    ghost_timestamps = pd.to_datetime(
        rng.choice(real_dates, size=n_ghost), utc=True
    ) + pd.to_timedelta(rng.integers(0, 3600, size=n_ghost), unit="s")

    ghost_revenue = rng.uniform(15.0, 350.0, size=n_ghost).round(2)

    ghost_df = pd.DataFrame({
        "order_id":         ghost_ids,
        "total_price":      ghost_revenue,
        "financial_status": "paid",
        "created_at_utc":   ghost_timestamps,
        "has_ga4_match":    False
    })
    print(f"[FM-01]  Ghost orders injected:         {n_ghost}  ({rate*100:.0f}% suppression rate)")
    return ghost_df

def build_matched_orders(df, fm03_rate, seed):
    """
    BLOCK 3 — BUILD MATCHED ORDERS (Shopify orders that DO have a GA4 match)
    Maps each valid GA4 transaction_id to a Shopify order_id (1:1).
    Adds realistic revenue. Injects FM-03 (phantom/voided purchases) at 5%.
    """
    rng = np.random.default_rng(seed + 1)
    n = len(df)

    # Revenue: use ga4_revenue where available, else generate synthetic
    ga4_rev = pd.to_numeric(df["ga4_revenue"], errors="coerce")
    synthetic_rev = rng.uniform(15.0, 350.0, size=n).round(2)
    revenue = ga4_rev.where(ga4_rev.notna() & (ga4_rev > 0), synthetic_rev)

    # FM-03: mark ~5% of matched orders as voided or refunded
    n_phantom = int(n * fm03_rate)
    phantom_idx = rng.choice(n, size=n_phantom, replace=False)
    financial_status = np.full(n, "paid", dtype=object)
    financial_status[phantom_idx] = rng.choice(
        ["voided", "refunded"], size=n_phantom
    )

    # Shopify created_at = GA4 event_timestamp + small realistic delay (0–300 sec)
    delay_seconds = pd.to_timedelta(
        rng.integers(0, 300, size=n), unit="s"
    )
    shopify_timestamps = df["event_timestamp_utc"].values + delay_seconds

    matched_df = pd.DataFrame({
        "order_id":         df["transaction_id"].values,
        "total_price":      revenue.values,
        "financial_status": financial_status,
        "created_at_utc":   pd.to_datetime(shopify_timestamps, utc=True),
        "has_ga4_match":    True
    })

    n_voided = (financial_status != "paid").sum()
    print(f"[FM-03]  Phantom/voided orders injected: {n_voided}  ({fm03_rate*100:.0f}% phantom rate)")
    return matched_df

def generate_setpoint(input_csv, output_csv):
    """
    BLOCK 4 — MASTER ORCHESTRATOR
    Runs all blocks in sequence, combines output, saves to CSV,
    and prints a Mass Balance summary so you can verify injection rates.
    """
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    print("=" * 60)
    print("  Shopify Setpoint Generator — Track B Project 4")
    print("=" * 60)

    # Step 1: Load GA4 seed
    ga4_df = load_ga4_seed(input_csv)

    # Step 2: Build matched Shopify orders (with FM-03 injected)
    matched_df = build_matched_orders(ga4_df, FM03_PHANTOM_RATE, RANDOM_SEED)

    # Step 3: Inject FM-01 ghost orders
    ghost_df = inject_fm01_ghost_orders(matched_df, FM01_SUPPRESSION_RATE, RANDOM_SEED)

    # Step 4: Combine and shuffle
    setpoint_df = pd.concat([matched_df, ghost_df], ignore_index=True)
    setpoint_df = setpoint_df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

    # Step 5: Save
    setpoint_df.to_csv(output_csv, index=False)

    # Step 6: Mass Balance summary
    total_orders      = len(setpoint_df)
    matched_orders    = setpoint_df["has_ga4_match"].sum()
    ghost_orders      = (~setpoint_df["has_ga4_match"]).sum()
    voided_orders     = (setpoint_df["financial_status"].isin(["voided","refunded"])).sum()
    paid_orders       = (setpoint_df["financial_status"] == "paid").sum()

    print()
    print("=" * 60)
    print("  MASS BALANCE SUMMARY (Engineering QA Check)")
    print("=" * 60)
    print(f"  Total Shopify orders generated:  {total_orders}")
    print(f"  Orders with GA4 match:           {matched_orders}  (Setpoint ∩ Sensor)")
    print(f"  Ghost orders (FM-01):            {ghost_orders}   (Setpoint only — no GA4 match)")
    print(f"  Voided/refunded orders (FM-03):  {voided_orders}   (GA4 fired, Shopify cancelled)")
    print(f"  Paid orders:                     {paid_orders}")
    print(f"  FM-01 rate (actual):             {ghost_orders/total_orders*100:.1f}%  (target: ~15%)")
    print(f"  FM-03 rate (actual):             {voided_orders/total_orders*100:.1f}%  (target: ~5%)")
    print()
    print(f"  Output saved to: {output_csv}")
    print("=" * 60)

    return setpoint_df

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path  = os.path.join(script_dir, INPUT_CSV)
    output_path = os.path.join(script_dir, OUTPUT_CSV)
    generate_setpoint(input_path, output_path)
