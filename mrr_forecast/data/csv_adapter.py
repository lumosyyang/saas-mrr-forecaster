"""
CSV file adapter for loading data from CSV files.
"""

import os
from typing import Optional
import pandas as pd
from mrr_forecast.data.base import DataSource


class CSVDataSource(DataSource):
    """
    Load forecast input data from CSV files.
    
    Expected file structure in data_dir:
        - subscriber_history.csv
        - attrition_rates.csv
        - gns_forecast.csv
        - arpc_history.csv
        - mom_change_rates.csv
        - arpc_overrides.csv (optional)
    """
    
    def __init__(self, data_dir: str):
        """
        Initialize with directory containing CSV files.
        
        Args:
            data_dir: Path to directory with CSV files
        """
        self.data_dir = data_dir
        if not os.path.isdir(data_dir):
            raise ValueError(f"Data directory not found: {data_dir}")
    
    def _read_csv(self, filename: str, parse_dates: list = None) -> pd.DataFrame:
        """Helper to read CSV with date parsing."""
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Required file not found: {filepath}")
        return pd.read_csv(filepath, parse_dates=parse_dates or [])
    
    def get_subscriber_history(self) -> pd.DataFrame:
        """Load subscriber history from CSV."""
        df = self._read_csv('subscriber_history.csv', parse_dates=['month_begin', 'cohort_month'])
        return df
    
    def get_attrition_rates(self) -> pd.DataFrame:
        """Load attrition rates from CSV."""
        return self._read_csv('attrition_rates.csv')
    
    def get_gns_forecast(self) -> pd.DataFrame:
        """Load GNS forecast from CSV."""
        df = self._read_csv('gns_forecast.csv', parse_dates=['month_begin'])
        return df
    
    def get_arpc_history(self) -> pd.DataFrame:
        """Load ARPC history from CSV."""
        df = self._read_csv('arpc_history.csv', parse_dates=['month_begin', 'cohort_month'])
        return df
    
    def get_mom_change_rates(self) -> pd.DataFrame:
        """Load MoM change rates from CSV."""
        df = self._read_csv('mom_change_rates.csv')
        if 'cohort_month' in df.columns:
            df['cohort_month'] = pd.to_datetime(df['cohort_month'])
        return df
    
    def get_arpc_overrides(self) -> Optional[pd.DataFrame]:
        """Load ARPC overrides from CSV (optional file)."""
        filepath = os.path.join(self.data_dir, 'arpc_overrides.csv')
        if not os.path.exists(filepath):
            return None
        df = pd.read_csv(filepath, parse_dates=['cohort_month'])
        # Filter active overrides
        if 'use_override_flag' in df.columns:
            df['use_override_flag'] = pd.to_numeric(df['use_override_flag'], errors='coerce')
            df = df[df['use_override_flag'] == 1]
        return df if len(df) > 0 else None
