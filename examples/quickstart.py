#!/usr/bin/env python3
"""
MRR Forecast - Quickstart Example
=================================
This example demonstrates how to run a basic MRR forecast
using the sample data provided.

Run from the mrr-forecast directory:
    python examples/quickstart.py
"""

import os
import sys
from datetime import date

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mrr_forecast import MRRForecaster, ForecastConfig
from mrr_forecast.data import CSVDataSource


def main():
    print("=" * 60)
    print("  MRR Forecast - Quickstart Demo")
    print("=" * 60)
    
    # 1. Configure the forecast
    # Sample data has month_begin = 2025-12-01, so we need:
    # base_date = Jan 2026, offset = -1 → base_month = Dec 2025
    config = ForecastConfig(
        segments=['Basic', 'Pro', 'Enterprise', 'Mobile'],
        base_date=date(2026, 1, 15),    # Use Jan 2026 as reference
        base_month_offset=-1,            # T0 = Dec 2025 (matches sample data)
        forecast_horizon_months=15,      # Forecast 15 months
        max_age=26,                      # Track ages 0-26
    )
    
    print(f"\nConfiguration:")
    print(f"  Base month (T0): {config.base_month}")
    print(f"  Forecast to: {config.forecast_end_month}")
    print(f"  Segments: {config.segments}")
    
    # 2. Load data from CSV files
    sample_data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'sample_data'
    )
    print(f"\nLoading data from: {sample_data_dir}")
    
    data_source = CSVDataSource(sample_data_dir)
    
    # 3. Run the forecast
    forecaster = MRRForecaster(config, data_source, verbose=True)
    results = forecaster.run()
    
    # 4. Display results
    print("\n" + "=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)
    
    # Show total MRR by month
    print("\n📊 Total MRR Forecast by Month:")
    print("-" * 50)
    mrr_total = results['mrr_total'].copy()
    mrr_total['month_begin'] = mrr_total['month_begin'].dt.strftime('%Y-%m')
    mrr_total['open_subscriber'] = mrr_total['open_subscriber'].round(0).astype(int)
    mrr_total['mrr'] = mrr_total['mrr'].round(2)
    mrr_total['arpc'] = mrr_total['arpc'].round(2)
    print(mrr_total.to_string(index=False))
    
    # Show MRR by segment for latest month
    print("\n📈 MRR by Segment (Latest Forecast Month):")
    print("-" * 50)
    mrr_summary = results['mrr_summary'].copy()
    latest_month = mrr_summary['month_begin'].max()
    latest = mrr_summary[mrr_summary['month_begin'] == latest_month].copy()
    latest['month_begin'] = latest['month_begin'].dt.strftime('%Y-%m')
    latest['open_subscriber'] = latest['open_subscriber'].round(0).astype(int)
    latest['mrr'] = latest['mrr'].round(2)
    latest['arpc'] = latest['arpc'].round(2)
    print(latest.to_string(index=False))
    
    # Summary stats
    print("\n📋 Forecast Statistics:")
    print("-" * 50)
    mrr_fcst = results['mrr_forecast']
    print(f"  Total forecast rows: {len(mrr_fcst):,}")
    print(f"  Segments: {mrr_fcst['segment'].nunique()}")
    print(f"  Months: {mrr_fcst['month_begin'].nunique()}")
    print(f"  Age cohorts: {mrr_fcst['age'].nunique()}")
    
    # Calculate growth
    mrr_total_df = results['mrr_total']
    if len(mrr_total_df) > 0:
        first_mrr = mrr_total_df['mrr'].iloc[0]
        last_mrr = mrr_total_df['mrr'].iloc[-1]
        growth = (last_mrr - first_mrr) / first_mrr * 100 if first_mrr != 0 else 0
        print(f"\n  MRR Growth (T0 → T{config.forecast_horizon_months}): {growth:.1f}%")
        print(f"  Starting MRR: ${first_mrr:,.2f}")
        print(f"  Ending MRR: ${last_mrr:,.2f}")
    else:
        print("\n  ⚠️  No MRR data to calculate growth (check data loading)")
    
    print("\n✅ Forecast complete!")
    print("=" * 60)
    
    return results


if __name__ == '__main__':
    main()
