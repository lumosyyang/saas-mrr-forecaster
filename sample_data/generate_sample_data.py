"""
Generate Synthetic Sample Data
==============================
Creates realistic fake data for testing the MRR forecast model.

Run this script to regenerate sample data:
    python sample_data/generate_sample_data.py
"""

import os
import numpy as np
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

# Configuration
SEGMENTS = ['Basic', 'Pro', 'Enterprise', 'Mobile']
MAX_AGE = 26
NUM_HISTORY_MONTHS = 24
BASE_DATE = date(2025, 12, 1)  # Base month for forecasting
FORECAST_MONTHS = 15
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Segment characteristics
SEGMENT_PARAMS = {
    'Basic': {
        'base_subs': 10000,
        'growth_rate': 0.02,
        'base_attrition': -0.08,
        'attrition_decay': 0.85,  # Attrition decreases with age
        'base_arpc': 15.0,
        'arpc_growth': 0.005,
    },
    'Pro': {
        'base_subs': 5000,
        'growth_rate': 0.03,
        'base_attrition': -0.05,
        'attrition_decay': 0.88,
        'base_arpc': 45.0,
        'arpc_growth': 0.008,
    },
    'Enterprise': {
        'base_subs': 1000,
        'growth_rate': 0.04,
        'base_attrition': -0.02,
        'attrition_decay': 0.92,
        'base_arpc': 150.0,
        'arpc_growth': 0.01,
    },
    'Mobile': {
        'base_subs': 8000,
        'growth_rate': 0.05,
        'base_attrition': -0.12,
        'attrition_decay': 0.82,
        'base_arpc': 10.0,
        'arpc_growth': 0.003,
    },
}

np.random.seed(42)  # For reproducibility


def generate_subscriber_history():
    """Generate historical subscriber data."""
    print("Generating subscriber history...")
    
    records = []
    
    for segment in SEGMENTS:
        params = SEGMENT_PARAMS[segment]
        
        for month_offset in range(-NUM_HISTORY_MONTHS + 1, 1):
            month_begin = BASE_DATE + relativedelta(months=month_offset)
            
            for age in range(0, MAX_AGE + 1):
                # Calculate cohort month
                if age >= MAX_AGE:
                    cohort_month = date(2099, 1, 1)  # Mature cohort placeholder
                else:
                    cohort_month = month_begin - relativedelta(months=age)
                
                # Base subscribers with growth and age decay
                growth_factor = 1 + params['growth_rate'] * month_offset / 12
                age_retention = params['attrition_decay'] ** age
                base = params['base_subs'] * growth_factor * age_retention / (MAX_AGE + 1)
                
                # Add some noise
                open_subscriber = max(0, base * (1 + np.random.normal(0, 0.05)))
                
                # New subscribers only at age 0
                new_subscriber = open_subscriber if age == 0 else 0
                
                # Calculate attrition (negative = loss)
                attrition_rate = params['base_attrition'] * (params['attrition_decay'] ** age)
                net_attrition = open_subscriber * attrition_rate * (1 + np.random.normal(0, 0.1))
                
                # Migration (small random flows)
                migrate_in = abs(np.random.normal(0, open_subscriber * 0.01))
                migrate_out = -abs(np.random.normal(0, open_subscriber * 0.01))
                
                records.append({
                    'month_begin': month_begin,
                    'segment': segment,
                    'age': age,
                    'cohort_month': cohort_month,
                    'open_subscriber': round(open_subscriber, 2),
                    'new_subscriber': round(new_subscriber, 2),
                    'net_attrition': round(net_attrition, 2),
                    'migrate_in': round(migrate_in, 2),
                    'migrate_out': round(migrate_out, 2),
                })
    
    df = pd.DataFrame(records)
    return df


def generate_attrition_rates():
    """Generate median attrition/migration rates."""
    print("Generating attrition rates...")
    
    records = []
    
    for segment in SEGMENTS:
        params = SEGMENT_PARAMS[segment]
        
        for age in range(0, MAX_AGE + 1):
            attrition_rate = params['base_attrition'] * (params['attrition_decay'] ** age)
            
            records.append({
                'segment': segment,
                'age': age,
                'median_attrition_rate': round(attrition_rate, 6),
                'median_inflow_rate': round(abs(np.random.normal(0, 0.005)), 6),
                'median_outflow_rate': round(-abs(np.random.normal(0, 0.005)), 6),
            })
    
    return pd.DataFrame(records)


def generate_gns_forecast():
    """Generate GNS (Gross New Subscriber) forecast."""
    print("Generating GNS forecast...")
    
    records = []
    
    for month_offset in range(1, FORECAST_MONTHS + 1):
        month_begin = BASE_DATE + relativedelta(months=month_offset)
        
        for segment in SEGMENTS:
            params = SEGMENT_PARAMS[segment]
            
            # Base GNS with growth and seasonality
            base_gns = params['base_subs'] * 0.1  # ~10% of base as monthly GNS
            growth = 1 + params['growth_rate'] * month_offset / 12
            
            # Add seasonality (higher in Q4)
            month = month_begin.month
            seasonality = 1.0 + 0.1 * (1 if month in [10, 11, 12] else 0)
            
            gns = base_gns * growth * seasonality * (1 + np.random.normal(0, 0.05))
            
            records.append({
                'month_begin': month_begin,
                'segment': segment,
                'new_subscriber_fcst': round(gns, 2),
            })
    
    return pd.DataFrame(records)


def generate_arpc_history():
    """Generate historical ARPC data."""
    print("Generating ARPC history...")
    
    records = []
    
    for segment in SEGMENTS:
        params = SEGMENT_PARAMS[segment]
        
        for month_offset in range(-NUM_HISTORY_MONTHS + 1, 1):
            month_begin = BASE_DATE + relativedelta(months=month_offset)
            
            for age in range(0, MAX_AGE + 1):
                # Cohort month
                if age >= MAX_AGE:
                    cohort_month = date(2099, 1, 1)
                else:
                    cohort_month = month_begin - relativedelta(months=age)
                
                # ARPC grows with age (discounts expire, price increases)
                base_arpc = params['base_arpc']
                age_growth = 1 + params['arpc_growth'] * age
                time_growth = 1 + params['arpc_growth'] * month_offset / 12
                
                arpc = base_arpc * age_growth * time_growth * (1 + np.random.normal(0, 0.02))
                
                records.append({
                    'month_begin': month_begin,
                    'segment': segment,
                    'age': age,
                    'cohort_month': cohort_month,
                    'arpc': round(arpc, 2),
                })
    
    return pd.DataFrame(records)


def generate_mom_change_rates():
    """Generate month-over-month ARPC change rates."""
    print("Generating MoM change rates...")
    
    records = []
    
    for segment in SEGMENTS:
        params = SEGMENT_PARAMS[segment]
        
        for age in range(0, MAX_AGE + 1):
            # MoM change is higher for young ages (discount expiration)
            if age <= 3:
                mom_change = params['arpc_growth'] * 2  # Higher early growth
            elif age <= 12:
                mom_change = params['arpc_growth']  # Normal growth
            else:
                mom_change = params['arpc_growth'] * 0.5  # Lower mature growth
            
            records.append({
                'segment': segment,
                'age': age,
                'avg_mom_pct_change': round(mom_change, 6),
            })
    
    return pd.DataFrame(records)


def generate_arpc_overrides():
    """Generate sample ARPC overrides for demonstration."""
    print("Generating ARPC overrides...")
    
    # Create overrides for the next few cohorts
    records = []
    
    for segment in ['Pro', 'Enterprise']:  # Only override some segments
        for month_offset in range(1, 4):
            cohort_month = BASE_DATE + relativedelta(months=month_offset)
            
            params = SEGMENT_PARAMS[segment]
            
            records.append({
                'segment': segment,
                'cohort_month': cohort_month,
                'age0_arpc_manual': round(params['base_arpc'] * 0.95, 2),  # 5% discount
                'mom_0_to_1_manual_pct': 0.02,
                'mom_1_to_2_manual_pct': 0.015,
                'mom_2_to_3_manual_pct': 0.01,
                'use_override_flag': 1,
            })
    
    return pd.DataFrame(records)


def main():
    """Generate all sample data files."""
    print(f"\nGenerating sample data in: {OUTPUT_DIR}\n")
    
    # Generate datasets
    subscriber_history = generate_subscriber_history()
    attrition_rates = generate_attrition_rates()
    gns_forecast = generate_gns_forecast()
    arpc_history = generate_arpc_history()
    mom_change_rates = generate_mom_change_rates()
    arpc_overrides = generate_arpc_overrides()
    
    # Save to CSV
    subscriber_history.to_csv(os.path.join(OUTPUT_DIR, 'subscriber_history.csv'), index=False)
    attrition_rates.to_csv(os.path.join(OUTPUT_DIR, 'attrition_rates.csv'), index=False)
    gns_forecast.to_csv(os.path.join(OUTPUT_DIR, 'gns_forecast.csv'), index=False)
    arpc_history.to_csv(os.path.join(OUTPUT_DIR, 'arpc_history.csv'), index=False)
    mom_change_rates.to_csv(os.path.join(OUTPUT_DIR, 'mom_change_rates.csv'), index=False)
    arpc_overrides.to_csv(os.path.join(OUTPUT_DIR, 'arpc_overrides.csv'), index=False)
    
    print("\nGenerated files:")
    print(f"  - subscriber_history.csv ({len(subscriber_history):,} rows)")
    print(f"  - attrition_rates.csv ({len(attrition_rates):,} rows)")
    print(f"  - gns_forecast.csv ({len(gns_forecast):,} rows)")
    print(f"  - arpc_history.csv ({len(arpc_history):,} rows)")
    print(f"  - mom_change_rates.csv ({len(mom_change_rates):,} rows)")
    print(f"  - arpc_overrides.csv ({len(arpc_overrides):,} rows)")
    print("\nDone!")


if __name__ == '__main__':
    main()
