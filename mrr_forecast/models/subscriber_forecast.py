"""
Subscriber Forecasting Model
============================
Forecasts open subscriber counts by segment and age cohort.

Algorithm:
1. Start with base month actuals (T0)
2. For each forecast month:
   - Age 0: new_subscriber = GNS forecast
   - Age 1-25: Roll forward from prior age with attrition/migration
   - Age 26: Roll forward from ages 25+26 (mature cohort bucket)
3. Apply median attrition, inflow, outflow rates
"""

import pandas as pd
import numpy as np
from typing import Optional
from mrr_forecast.config.model_config import ForecastConfig
from mrr_forecast.utils.helpers import add_months, ForecastLogger


class SubscriberForecaster:
    """
    Forecasts subscriber counts by segment and age cohort.
    
    Uses cohort-based modeling with:
    - Historical attrition rates
    - Migration flows between segments
    - GNS (Gross New Subscriber) forecasts for age 0
    """
    
    def __init__(self, config: ForecastConfig, logger: Optional[ForecastLogger] = None):
        """
        Initialize the forecaster.
        
        Args:
            config: Forecast configuration
            logger: Optional logger for progress
        """
        self.config = config
        self.logger = logger or ForecastLogger(verbose=False)
    
    def forecast(
        self,
        base_month_actuals: pd.DataFrame,
        attrition_rates: pd.DataFrame,
        gns_forecast: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Generate subscriber forecast.
        
        Args:
            base_month_actuals: Actual subscriber data for base month (T0)
                Required columns: segment, age, cohort_month, open_subscriber
            attrition_rates: Median rates by segment and age
                Required columns: segment, age, median_attrition_rate, 
                                  median_inflow_rate, median_outflow_rate
            gns_forecast: GNS forecast by segment and month
                Required columns: month_begin, segment, new_subscriber_fcst
        
        Returns:
            DataFrame with subscriber forecast including:
                fcst_ind, month_begin, segment, age, cohort_month,
                new_subscriber, open_subscriber, net_attrition, migrate_in, migrate_out
        """
        self.logger.log("Running subscriber forecast...")
        
        # Prepare data
        base_df = self._prepare_base_data(base_month_actuals)
        rates_df = self._prepare_rates(attrition_rates)
        gns_df = self._prepare_gns(gns_forecast)
        
        base_month = pd.to_datetime(self.config.base_month)
        forecast_frames = []
        current_df = base_df[['month_begin', 'segment', 'age', 'cohort_month', 'open_subscriber']].copy()
        
        # Forecast each month
        for step in range(1, self.config.forecast_horizon_months + 1):
            forecast_month = base_month + pd.DateOffset(months=step)
            self.logger.log(f"  Month {step}: {forecast_month.strftime('%Y-%m')}")
            
            # Roll forward to next month
            tN = self._forecast_one_month(
                current_df, rates_df, gns_df, forecast_month
            )
            
            forecast_frames.append(tN)
            current_df = tN[['month_begin', 'segment', 'age', 'cohort_month', 'open_subscriber']].copy()
        
        # Combine actuals + forecast
        base_out = base_df.copy()
        base_out['fcst_ind'] = 'actual'
        
        full_result = pd.concat([base_out] + forecast_frames, ignore_index=True)
        
        self.logger.log(f"  Subscriber forecast complete: {len(full_result):,} rows")
        return full_result
    
    def _prepare_base_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare base month data."""
        result = df.copy()
        result['month_begin'] = pd.to_datetime(result['month_begin'])
        result['cohort_month'] = pd.to_datetime(result['cohort_month'])
        return result
    
    def _prepare_rates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare attrition rates data."""
        result = df.copy()
        # Ensure numeric columns
        for col in ['median_attrition_rate', 'median_inflow_rate', 'median_outflow_rate']:
            if col in result.columns:
                result[col] = pd.to_numeric(result[col], errors='coerce').fillna(0)
        return result
    
    def _prepare_gns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare GNS forecast data."""
        result = df.copy()
        result['month_begin'] = pd.to_datetime(result['month_begin'])
        return result
    
    def _forecast_one_month(
        self,
        current_df: pd.DataFrame,
        rates_df: pd.DataFrame,
        gns_df: pd.DataFrame,
        forecast_month: pd.Timestamp
    ) -> pd.DataFrame:
        """Forecast one month forward."""
        
        max_age = self.config.max_age
        mature_date = pd.to_datetime(self.config.mature_cohort_date)
        
        # Prepare base: shift month and cohort forward
        tN = current_df.copy()
        tN['month_begin'] = forecast_month
        tN['cohort_month'] = tN['cohort_month'].apply(
            lambda x: x if x == mature_date else x + pd.DateOffset(months=1)
        )
        
        # Get GNS for this month
        gns_this_month = gns_df[gns_df['month_begin'] == forecast_month].copy()
        tN = tN.merge(
            gns_this_month[['segment', 'new_subscriber_fcst']].rename(
                columns={'new_subscriber_fcst': 'gns_fcst'}
            ),
            on='segment',
            how='left'
        )
        
        # Merge rates
        tN = tN.merge(rates_df, on=['segment', 'age'], how='left')
        
        # Fill missing rates with 0
        for col in ['median_attrition_rate', 'median_inflow_rate', 'median_outflow_rate']:
            if col in tN.columns:
                tN[col] = tN[col].fillna(0)
        
        # Calculate prior_subs (subscribers rolling into this age)
        tN['prior_subs'] = 0.0
        
        for segment in tN['segment'].unique():
            seg_mask = tN['segment'] == segment
            seg_df = tN[seg_mask].copy()
            
            for age in range(0, max_age + 1):
                age_mask = seg_mask & (tN['age'] == age)
                
                if age == 0:
                    # Age 0: prior_subs = new subscribers (GNS forecast)
                    gns_val = tN.loc[age_mask, 'gns_fcst'].iloc[0] if age_mask.any() else 0
                    tN.loc[age_mask, 'prior_subs'] = gns_val if pd.notna(gns_val) else 0
                    
                elif age == max_age:
                    # Max age: accumulate from age-1 and age=max_age
                    prior_ages = seg_df[seg_df['age'].isin([max_age - 1, max_age])]
                    tN.loc[age_mask, 'prior_subs'] = prior_ages['open_subscriber'].sum()
                    
                else:
                    # Middle ages: roll from age-1
                    prior_age = seg_df[seg_df['age'] == age - 1]
                    if not prior_age.empty:
                        tN.loc[age_mask, 'prior_subs'] = prior_age['open_subscriber'].iloc[0]
        
        # Calculate forecast metrics
        tN['fcst_ind'] = 'fcst'
        
        # New subscribers (only age 0)
        tN['new_subscriber'] = np.where(tN['age'] == 0, tN['prior_subs'], np.nan)
        
        # Net attrition
        tN['net_attrition'] = tN['prior_subs'] * tN['median_attrition_rate']
        
        # Migration
        tN['migrate_in'] = tN['prior_subs'] * tN['median_inflow_rate']
        tN['migrate_out'] = tN['prior_subs'] * tN['median_outflow_rate']
        
        # Open subscribers = prior + attrition + migration
        tN['open_subscriber'] = (
            tN['prior_subs'] 
            + tN['net_attrition'] 
            + tN['migrate_in'] 
            + tN['migrate_out']
        )
        
        # Select output columns
        output_cols = [
            'fcst_ind', 'month_begin', 'segment', 'age', 'cohort_month',
            'new_subscriber', 'open_subscriber', 'net_attrition', 
            'migrate_in', 'migrate_out'
        ]
        
        return tN[output_cols]
