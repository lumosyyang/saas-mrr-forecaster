"""
MRR Calculator
==============
Combines subscriber forecast and ARPC forecast to calculate MRR.

Formula: MRR = Open Subscribers × ARPC
"""

import pandas as pd
from typing import Optional
from mrr_forecast.config.model_config import ForecastConfig
from mrr_forecast.utils.helpers import ForecastLogger


class MRRCalculator:
    """
    Calculates Monthly Recurring Revenue from subscriber and ARPC forecasts.
    
    MRR = Open Subscribers × ARPC
    """
    
    def __init__(self, config: ForecastConfig, logger: Optional[ForecastLogger] = None):
        """
        Initialize the calculator.
        
        Args:
            config: Forecast configuration
            logger: Optional logger for progress
        """
        self.config = config
        self.logger = logger or ForecastLogger(verbose=False)
    
    def calculate(
        self,
        subscriber_forecast: pd.DataFrame,
        arpc_forecast: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate MRR from subscriber and ARPC forecasts.
        
        Args:
            subscriber_forecast: Subscriber forecast
                Required columns: month_begin, segment, age, cohort_month, open_subscriber
            arpc_forecast: ARPC forecast
                Required columns: month_begin, segment, age, cohort_month, arpc
        
        Returns:
            DataFrame with MRR forecast including:
                month_begin, segment, age, cohort_month, open_subscriber, arpc, mrr
        """
        self.logger.log("Calculating MRR...")
        
        # Prepare dataframes
        subs_df = subscriber_forecast.copy()
        arpc_df = arpc_forecast.copy()
        
        # Ensure date columns are datetime
        for col in ['month_begin', 'cohort_month']:
            subs_df[col] = pd.to_datetime(subs_df[col])
            arpc_df[col] = pd.to_datetime(arpc_df[col])
        
        # Merge subscriber and ARPC forecasts
        mrr_df = subs_df.merge(
            arpc_df[['month_begin', 'segment', 'age', 'cohort_month', 'arpc']],
            on=['month_begin', 'segment', 'age', 'cohort_month'],
            how='left'
        )
        
        # Calculate MRR
        mrr_df['mrr'] = mrr_df['open_subscriber'] * mrr_df['arpc']
        
        self.logger.log(f"  MRR calculation complete: {len(mrr_df):,} rows")
        
        return mrr_df
    
    def summarize(
        self,
        mrr_forecast: pd.DataFrame,
        group_by: list = None
    ) -> pd.DataFrame:
        """
        Summarize MRR forecast by specified dimensions.
        
        Args:
            mrr_forecast: Full MRR forecast DataFrame
            group_by: Columns to group by (default: ['month_begin', 'segment'])
        
        Returns:
            Summarized MRR DataFrame
        """
        if group_by is None:
            group_by = ['month_begin', 'segment']
        
        summary = mrr_forecast.groupby(group_by).agg({
            'open_subscriber': 'sum',
            'mrr': 'sum'
        }).reset_index()
        
        # Calculate implied ARPC
        summary['arpc'] = summary['mrr'] / summary['open_subscriber']
        
        return summary
    
    def summarize_total(self, mrr_forecast: pd.DataFrame) -> pd.DataFrame:
        """
        Get total MRR by month (across all segments).
        
        Args:
            mrr_forecast: Full MRR forecast DataFrame
        
        Returns:
            Monthly total MRR summary
        """
        return self.summarize(mrr_forecast, group_by=['month_begin'])
