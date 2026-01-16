"""
DataFrame adapter for loading data from pandas DataFrames.
Useful for programmatic data generation or testing.
"""

from typing import Optional
import pandas as pd
from mrr_forecast.data.base import DataSource


class DataFrameSource(DataSource):
    """
    Load forecast input data from pandas DataFrames.
    
    Useful for:
        - Programmatic data generation
        - Testing with synthetic data
        - In-memory data pipelines
    """
    
    def __init__(
        self,
        subscriber_history: pd.DataFrame,
        attrition_rates: pd.DataFrame,
        gns_forecast: pd.DataFrame,
        arpc_history: pd.DataFrame,
        mom_change_rates: pd.DataFrame,
        arpc_overrides: Optional[pd.DataFrame] = None
    ):
        """
        Initialize with DataFrames.
        
        Args:
            subscriber_history: Historical subscriber data
            attrition_rates: Median attrition/migration rates
            gns_forecast: GNS forecast by segment
            arpc_history: Historical ARPC data
            mom_change_rates: MoM ARPC change rates
            arpc_overrides: Optional manual ARPC overrides
        """
        self._subscriber_history = subscriber_history.copy()
        self._attrition_rates = attrition_rates.copy()
        self._gns_forecast = gns_forecast.copy()
        self._arpc_history = arpc_history.copy()
        self._mom_change_rates = mom_change_rates.copy()
        self._arpc_overrides = arpc_overrides.copy() if arpc_overrides is not None else None
    
    def get_subscriber_history(self) -> pd.DataFrame:
        return self._subscriber_history.copy()
    
    def get_attrition_rates(self) -> pd.DataFrame:
        return self._attrition_rates.copy()
    
    def get_gns_forecast(self) -> pd.DataFrame:
        return self._gns_forecast.copy()
    
    def get_arpc_history(self) -> pd.DataFrame:
        return self._arpc_history.copy()
    
    def get_mom_change_rates(self) -> pd.DataFrame:
        return self._mom_change_rates.copy()
    
    def get_arpc_overrides(self) -> Optional[pd.DataFrame]:
        if self._arpc_overrides is None:
            return None
        df = self._arpc_overrides.copy()
        if 'use_override_flag' in df.columns:
            df['use_override_flag'] = pd.to_numeric(df['use_override_flag'], errors='coerce')
            df = df[df['use_override_flag'] == 1]
        return df if len(df) > 0 else None
