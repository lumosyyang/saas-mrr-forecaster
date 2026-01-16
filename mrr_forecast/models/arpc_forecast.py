"""
ARPC (Average Revenue Per Customer) Forecasting Model
======================================================
Forecasts ARPC by segment and age cohort.

Algorithm:
1. Start with base month ARPC (T0)
2. For each forecast month:
   - Age 0: Use rolling average or manual override
   - Age 1-25: Apply MoM % change to prior age's ARPC
   - Age 26: Cap at historical average (mature cohort)
3. MoM changes capture price increases, discount expirations
"""

import pandas as pd
import numpy as np
from typing import Optional
from mrr_forecast.config.model_config import ForecastConfig
from mrr_forecast.utils.helpers import add_months, ForecastLogger


class ARPCForecaster:
    """
    Forecasts ARPC (Average Revenue Per Customer) by segment and age cohort.
    
    Uses MoM (month-over-month) change rates to project ARPC forward,
    with special handling for:
    - Age 0: Rolling average or manual overrides
    - Age 26+: Capped at mature cohort average
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
        base_month_arpc: pd.DataFrame,
        mom_change_rates: pd.DataFrame,
        age0_avg_arpc: pd.DataFrame,
        age26_avg_arpc: pd.DataFrame,
        overrides: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Generate ARPC forecast.
        
        Args:
            base_month_arpc: Actual ARPC for base month (T0)
                Required columns: segment, age, cohort_month, arpc
            mom_change_rates: MoM ARPC change rates
                Required columns: segment, age, avg_mom_pct_change
            age0_avg_arpc: Rolling average ARPC for age 0
                Required columns: segment, age0_avg_arpc
            age26_avg_arpc: Average ARPC for mature cohorts
                Required columns: segment, age26_avg_arpc
            overrides: Optional manual overrides
                Required columns: segment, cohort_month, age0_arpc_manual,
                                  mom_0_to_1_manual_pct, etc.
        
        Returns:
            DataFrame with ARPC forecast including:
                fcst_ind, month_begin, segment, age, cohort_month, arpc
        """
        self.logger.log("Running ARPC forecast...")
        
        # Prepare inputs
        base_df = self._prepare_base_arpc(base_month_arpc)
        mom_df = self._prepare_mom_rates(mom_change_rates)
        age0_df = self._prepare_age0_avg(age0_avg_arpc)
        age26_df = self._prepare_age26_avg(age26_avg_arpc)
        
        if overrides is not None and self.config.enable_arpc_overrides:
            overrides = self._prepare_overrides(overrides)
            self.logger.log(f"  Using {len(overrides)} manual overrides")
        else:
            overrides = None
        
        base_month = pd.to_datetime(self.config.base_month)
        forecast_frames = []
        current_df = base_df[['month_begin', 'segment', 'age', 'cohort_month', 'arpc']].copy()
        
        # Forecast each month
        for step in range(1, self.config.forecast_horizon_months + 1):
            forecast_month = base_month + pd.DateOffset(months=step)
            self.logger.log(f"  Month {step}: {forecast_month.strftime('%Y-%m')}")
            
            tN = self._forecast_one_month(
                current_df, mom_df, age0_df, age26_df, overrides, forecast_month
            )
            
            forecast_frames.append(tN)
            current_df = tN[['month_begin', 'segment', 'age', 'cohort_month', 'arpc']].copy()
        
        # Combine actuals + forecast
        base_out = base_df.copy()
        base_out['fcst_ind'] = 'actual'
        
        full_result = pd.concat([base_out] + forecast_frames, ignore_index=True)
        
        self.logger.log(f"  ARPC forecast complete: {len(full_result):,} rows")
        return full_result
    
    def _prepare_base_arpc(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare base month ARPC data."""
        result = df.copy()
        result['month_begin'] = pd.to_datetime(result['month_begin'])
        result['cohort_month'] = pd.to_datetime(result['cohort_month'])
        result['arpc'] = pd.to_numeric(result['arpc'], errors='coerce')
        return result
    
    def _prepare_mom_rates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare MoM change rates."""
        result = df.copy()
        result['avg_mom_pct_change'] = pd.to_numeric(result['avg_mom_pct_change'], errors='coerce').fillna(0)
        return result
    
    def _prepare_age0_avg(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare age 0 average ARPC."""
        result = df.copy()
        result['age0_avg_arpc'] = pd.to_numeric(result['age0_avg_arpc'], errors='coerce')
        return result
    
    def _prepare_age26_avg(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare age 26 average ARPC."""
        result = df.copy()
        result['age26_avg_arpc'] = pd.to_numeric(result['age26_avg_arpc'], errors='coerce')
        return result
    
    def _prepare_overrides(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare manual overrides."""
        result = df.copy()
        result['cohort_month'] = pd.to_datetime(result['cohort_month'])
        for col in ['age0_arpc_manual', 'mom_0_to_1_manual_pct', 
                    'mom_1_to_2_manual_pct', 'mom_2_to_3_manual_pct']:
            if col in result.columns:
                result[col] = pd.to_numeric(result[col], errors='coerce')
        return result
    
    def _forecast_one_month(
        self,
        current_df: pd.DataFrame,
        mom_df: pd.DataFrame,
        age0_df: pd.DataFrame,
        age26_df: pd.DataFrame,
        overrides: Optional[pd.DataFrame],
        forecast_month: pd.Timestamp
    ) -> pd.DataFrame:
        """Forecast ARPC one month forward."""
        
        max_age = self.config.max_age
        mature_date = pd.to_datetime(self.config.mature_cohort_date)
        
        # Prepare base
        tN = current_df.copy()
        tN['month_begin'] = forecast_month
        tN['prior_cohort_month'] = tN['cohort_month']
        tN['cohort_month'] = tN['cohort_month'].apply(
            lambda x: x if x == mature_date else x + pd.DateOffset(months=1)
        )
        tN['prior_age'] = tN['age']
        tN['prior_arpc'] = tN['arpc']
        
        # Merge MoM rates
        tN = tN.merge(
            mom_df[['segment', 'age', 'avg_mom_pct_change']],
            on=['segment', 'age'],
            how='left'
        )
        tN['avg_mom_pct_change'] = tN['avg_mom_pct_change'].fillna(0)
        
        # Merge age 0 and age 26 averages
        tN = tN.merge(age0_df[['segment', 'age0_avg_arpc']], on='segment', how='left')
        tN = tN.merge(age26_df[['segment', 'age26_avg_arpc']], on='segment', how='left')
        
        # Calculate ARPC for each row
        tN['arpc'] = tN.apply(
            lambda row: self._calc_arpc(row, overrides, max_age),
            axis=1
        )
        
        tN['fcst_ind'] = 'fcst'
        
        # Select output columns
        return tN[['fcst_ind', 'month_begin', 'segment', 'age', 'cohort_month', 'arpc']]
    
    def _calc_arpc(self, row: pd.Series, overrides: Optional[pd.DataFrame], max_age: int) -> float:
        """Calculate ARPC for a single row."""
        age = row['age']
        segment = row['segment']
        cohort = row['cohort_month']
        prior_arpc = row.get('prior_arpc', 0)
        mom_rate = row.get('avg_mom_pct_change', 0)
        
        # Age 0: Use rolling average or manual override
        if age == 0:
            # Check for manual override
            if overrides is not None:
                override = overrides[
                    (overrides['segment'] == segment) & 
                    (overrides['cohort_month'] == cohort)
                ]
                if not override.empty and pd.notna(override['age0_arpc_manual'].iloc[0]):
                    return override['age0_arpc_manual'].iloc[0]
            
            # Fall back to rolling average
            return row.get('age0_avg_arpc', prior_arpc) or prior_arpc
        
        # Age 26 (mature): Cap at historical average
        if age == max_age:
            return row.get('age26_avg_arpc', prior_arpc) or prior_arpc
        
        # Middle ages: Apply MoM change
        # Check for manual override on early ages
        if age in [1, 2, 3] and overrides is not None:
            override = overrides[
                (overrides['segment'] == segment) & 
                (overrides['cohort_month'] == cohort)
            ]
            if not override.empty:
                override_col = f'mom_{age-1}_to_{age}_manual_pct'
                if override_col in override.columns:
                    manual_mom = override[override_col].iloc[0]
                    if pd.notna(manual_mom):
                        mom_rate = manual_mom
        
        # Apply MoM rate
        return prior_arpc * (1 + mom_rate)
