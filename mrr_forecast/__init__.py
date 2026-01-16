"""
MRR Forecast - A modular framework for forecasting Monthly Recurring Revenue.
"""

__version__ = "0.1.0"

from mrr_forecast.runner import MRRForecaster
from mrr_forecast.config.model_config import ForecastConfig

__all__ = ["MRRForecaster", "ForecastConfig"]
