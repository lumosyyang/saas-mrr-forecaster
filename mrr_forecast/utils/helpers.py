"""
Utility functions for MRR forecasting.
"""

import logging
from datetime import date
from dateutil.relativedelta import relativedelta
import pandas as pd


def add_months(d: date, months: int) -> date:
    """
    Add months to a date.
    
    Args:
        d: Base date
        months: Number of months to add (can be negative)
    
    Returns:
        New date with months added
    """
    if isinstance(d, pd.Timestamp):
        d = d.date()
    return d + relativedelta(months=months)


def first_of_month(d: date) -> date:
    """Get the first day of the month for a given date."""
    if isinstance(d, pd.Timestamp):
        d = d.date()
    return d.replace(day=1)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Get a configured logger.
    
    Args:
        name: Logger name
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '[%(name)s] %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


class ForecastLogger:
    """Simple logger for forecast progress."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self._logger = get_logger('MRR-Forecast')
    
    def log(self, message: str):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            self._logger.info(message)
    
    def log_step(self, step_name: str):
        """Log a major step."""
        self.log(f"\n{'='*60}")
        self.log(f"  {step_name}")
        self.log(f"{'='*60}")
    
    def log_result(self, table_name: str, row_count: int):
        """Log result creation."""
        self.log(f"  Created: {table_name} ({row_count:,} rows)")
