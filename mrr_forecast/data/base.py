"""
Abstract base class for data sources.
Implement this interface to connect to your own data.
"""

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class DataSource(ABC):
    """
    Abstract base class for data sources.
    
    Implement this interface to load data from your preferred source
    (CSV files, databases, data warehouses, etc.)
    """
    
    @abstractmethod
    def get_subscriber_history(self) -> pd.DataFrame:
        """
        Get historical subscriber data by segment, age, and cohort.
        
        Required columns:
            - month_begin: date (first of month)
            - segment: str (segment name)
            - age: int (months since GNS, 0-26+)
            - cohort_month: date (GNS cohort month)
            - open_subscriber: float (subscriber count)
            - new_subscriber: float (new subscribers this month)
            - net_attrition: float (net subscriber change from attrition)
            - migrate_in: float (subscribers migrating in from other segments)
            - migrate_out: float (subscribers migrating out to other segments)
        
        Returns:
            DataFrame with subscriber history
        """
        pass
    
    @abstractmethod
    def get_attrition_rates(self) -> pd.DataFrame:
        """
        Get historical attrition/migration rates by segment and age.
        
        Required columns:
            - segment: str
            - age: int
            - median_attrition_rate: float (median monthly attrition rate)
            - median_inflow_rate: float (median monthly inflow rate)
            - median_outflow_rate: float (median monthly outflow rate)
        
        Returns:
            DataFrame with median rates
        """
        pass
    
    @abstractmethod
    def get_gns_forecast(self) -> pd.DataFrame:
        """
        Get forecasted Gross New Subscribers by segment and month.
        
        Required columns:
            - month_begin: date
            - segment: str
            - new_subscriber_fcst: float (forecasted new subscribers)
        
        Returns:
            DataFrame with GNS forecast
        """
        pass
    
    @abstractmethod
    def get_arpc_history(self) -> pd.DataFrame:
        """
        Get historical ARPC by segment, age, and cohort.
        
        Required columns:
            - month_begin: date
            - segment: str
            - age: int
            - cohort_month: date
            - arpc: float (average revenue per customer)
        
        Returns:
            DataFrame with ARPC history
        """
        pass
    
    @abstractmethod
    def get_mom_change_rates(self) -> pd.DataFrame:
        """
        Get month-over-month ARPC change rates by segment, age, and cohort.
        
        Required columns:
            - segment: str
            - age: int
            - cohort_month: date (optional, for cohort-specific rates)
            - avg_mom_pct_change: float (average MoM % change)
        
        Returns:
            DataFrame with MoM rates
        """
        pass
    
    def get_arpc_overrides(self) -> Optional[pd.DataFrame]:
        """
        Get manual ARPC overrides for specific cohorts (optional).
        
        Required columns if provided:
            - segment: str
            - cohort_month: date
            - age0_arpc_manual: float (manual age-0 ARPC override)
            - mom_0_to_1_manual_pct: float (manual MoM from age 0 to 1)
            - mom_1_to_2_manual_pct: float (manual MoM from age 1 to 2)
            - mom_2_to_3_manual_pct: float (manual MoM from age 2 to 3)
            - use_override_flag: int (1 to use, 0 to skip)
        
        Returns:
            DataFrame with overrides, or None if not available
        """
        return None
