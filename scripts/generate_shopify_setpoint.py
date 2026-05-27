import pandas as pd
import numpy as np
import random
from datetime import timedelta

# --- CONFIGURATION ---
INPUT_FILE = 'ga4_baseline.csv' # Make sure this matches your downloaded file name
OUTPUT_FILE = 'shopify_orders_setpoint.csv'
FM1_SUPPRESSION_RATE = 0.15     # 15% of Shopify orders never made it to GA4 (Ad-blockers)
FM3_PHANTOM_RATE = 0.05         # 5% of GA4 purchases were actually cancelled/voided

def load_ga4_sensor_data(filepath):
    """Loads the GA4 baseline data to use as the architectural spine."""
    try:
        df = pd.read_csv(filepath)
        # Rename columns to ensure consistency regardless of which query you ran
        df.columns = ['transaction_id', 'revenue', 'event_date', 'timestamp_utc']
        return df
    except FileNotFoundError:
        print(f"ERROR: Could not find {filepath}. Ensure it is in the /scripts folder.")
        exit()

def inject_fmea_leaks(ga4_df):
    """
    Applies our Chemical Engineering FMEA principles to generate the Shopify Ground Truth.
    """
    # 1. Base Set: Orders that perfectly match between GA4 and Shopify
    shopify_orders = pd.DataFrame({
        'order_id': ga4_df['transaction_id'],
        'total_price': ga4_df['revenue'],
        'financial_status': 'paid',
        'created_at_utc': pd.to_datetime(ga4_df['timestamp_utc']) - pd.to_timedelta(np.random.randint(1, 10, len(ga4_df)), unit='s')
        # Shopify timestamps are usually slightly *before* the GA4 purchase event fires
    })

    # 2. Inject Failure Mode 3: Phantom Purchases (Cancelled/Voided)
    # GA4 fired the tag, but Shopify later marked it as voided.
    num_phantoms = int(len(shopify_orders) * FM3_PHANTOM_RATE)
    phantom_indices = random.sample(range(len(shopify_orders)), num_phantoms)
    shopify_orders.loc[phantom_indices, 'financial_status'] = 'voided'

    # 3. Inject Failure Mode 1: Client-Side Suppression (Ad-Blockers)
    # These are real Shopify orders that GA4 NEVER saw.
    num_suppressed = int(len(shopify_orders) * (FM1_SUPPRESSION_RATE / (1 - FM1_SUPPRESSION_RATE)))
    
    suppressed_orders = pd.DataFrame({
        'order_id': ['SHP-' + str(random.randint(100000, 999999)) for _ in range(num_suppressed)],
        'total_price': [round(random.uniform(15.0, 150.0), 2) for _ in range(num_suppressed)],
        'financial_status': 'paid',
        # Distribute these randomly over the January 2021 timeframe
        'created_at_utc': pd.to_datetime('2021-01-01') + pd.to_timedelta(np.random.randint(0, 31*24*60*60, num_suppressed), unit='s')
    })
    
    # Combine the matched orders and the suppressed orders
    final_shopify_df = pd.concat([shopify_orders, suppressed_orders], ignore_index=True)
    
    # Shuffle the dataset so the injected orders aren't just at the bottom
    final_shopify_df = final_shopify_df.sample(frac=1).reset_index(drop=True)
    
    return final_shopify_df, len(ga4_df), num_suppressed, num_phantoms

if __name__ == "__main__":
    print("Initializing Shopify Setpoint Generator...")
    
    ga4_data = load_ga4_sensor_data(INPUT_FILE)
    final_data, original_ga4_count, fm1_count, fm3_count = inject_fmea_leaks(ga4_data)
    
    # Export to CSV
    final_data.to_csv(OUTPUT_FILE, index=False)
    
    # Engineering Output: The Pre-SQL Mass Balance Check
    print("\n--- MASS BALANCE INJECTION REPORT ---")
    print(f"Sensor Read (GA4 Valid Transactions): {original_ga4_count}")
    print(f"Setpoint Generated (Total Shopify Orders): {len(final_data)}")
    print(f"  -> Valid/Matched Orders: {original_ga4_count - fm3_count}")
    print(f"  -> FM1 (Suppressed/Missing in GA4): {fm1_count} orders injected")
    print(f"  -> FM3 (Voided/Phantom in GA4): {fm3_count} orders injected")
    print(f"Output saved to: {OUTPUT_FILE}")
    print("-------------------------------------\n")
