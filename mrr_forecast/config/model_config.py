"""
MRR Forecast Configuration
==========================
Central configuration for the forecasting model.
Customize these settings for your business.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional
from dateutil.relativedelta import relativedelta


@dataclass
class ForecastConfig:
    """
    Configuration for the MRR forecasting model.
    
    Attributes:
        segments: List of segment names to forecast (e.g., ['Basic', 'Pro', 'Enterprise'])
        base_date: The reference date for forecasting (defaults to today)
        base_month_offset: Months back from base_date for T0 (default: -1 = last completed month)
        forecast_horizon_months: Number of months to forecast forward (default: 15)
        historical_lookback_months: Months of history for rate calculations (default: 12)
        max_age: Maximum age cohort to track separately (default: 26, older grouped together)
        mature_cohort_date: Placeholder date for mature cohorts (default: 2099-01-01)
        enable_arpc_overrides: Whether to apply manual ARPC overrides (default: True)
    """
    
    # Segment definitions - customize for your business
    segments: List[str] = field(default_factory=lambda: [
        'Basic',
        'Pro', 
        'Enterprise',
        'Mobile',
    ])
    
    # Date configuration
    base_date: date = field(default_factory=date.today)
    base_month_offset: int = -1  # T0 is last completed month
    forecast_horizon_months: int = 15
    historical_lookback_months: int = 12
    
    # Age cohort configuration
    min_age: int = 0
    max_age: int = 26  # Customers older than this are bucketed together
    mature_cohort_date: str = '2099-01-01'
    
    # ARPC configuration
    enable_arpc_overrides: bool = True
    age0_arpc_rolling_window: int = 4  # Months for rolling average of age-0 ARPC
    
    # Early life ages eligible for manual MoM overrides
    early_life_ages: List[int] = field(default_factory=lambda: [0, 1, 2, 3])
    
    @property
    def base_month(self) -> date:
        """Get the base month (T0) for forecasting."""
        ref = self.base_date.replace(day=1)
        return ref + relativedelta(months=self.base_month_offset)
    
    @property
    def forecast_end_month(self) -> date:
        """Get the last month of the forecast period."""
        return self.base_month + relativedelta(months=self.forecast_horizon_months)
    
    @property
    def historical_start(self) -> date:
        """Get start date for historical rate calculations."""
        return self.base_month + relativedelta(months=-self.historical_lookback_months)
    
    def get_age_range(self) -> range:
        """Get the range of age cohorts."""
        return range(self.min_age, self.max_age + 1)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.max_age < 1:
            raise ValueError("max_age must be at least 1")
        if self.forecast_horizon_months < 1:
            raise ValueError("forecast_horizon_months must be at least 1")
        if self.historical_lookback_months < 1:
            raise ValueError("historical_lookback_months must be at least 1")
        if not self.segments:
            raise ValueError("At least one segment must be defined")


# Default configuration instance
DEFAULT_CONFIG = ForecastConfig()


def create_config(
    segments: Optional[List[str]] = None,
    forecast_months: int = 15,
    max_age: int = 26,
    **kwargs
) -> ForecastConfig:
    """
    Factory function to create a ForecastConfig with common customizations.
    
    Args:
        segments: List of segment names
        forecast_months: Number of months to forecast
        max_age: Maximum age cohort
        **kwargs: Additional config parameters
        
    Returns:
        Configured ForecastConfig instance
    """
    config_kwargs = {
        'forecast_horizon_months': forecast_months,
        'max_age': max_age,
        **kwargs
    }
    if segments:
        config_kwargs['segments'] = segments
    
    return ForecastConfig(**config_kwargs)
