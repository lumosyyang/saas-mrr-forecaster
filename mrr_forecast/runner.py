"""
MRR Forecast Runner
===================
Main orchestration class for running the full forecast pipeline.
"""

import pandas as pd
from typing import Optional, Dict, Any
from mrr_forecast.config.model_config import ForecastConfig
from mrr_forecast.data.base import DataSource
from mrr_forecast.models.subscriber_forecast import SubscriberForecaster
from mrr_forecast.models.arpc_forecast import ARPCForecaster
from mrr_forecast.models.mrr_calculator import MRRCalculator
from mrr_forecast.utils.helpers import ForecastLogger


class MRRForecaster:
    """
    Main class to orchestrate the full MRR forecasting pipeline.
    
    Pipeline:
        1. Load data from DataSource
        2. Run subscriber forecast
        3. Run ARPC forecast
        4. Calculate MRR = Subscribers × ARPC
    
    Usage:
        from mrr_forecast import MRRForecaster, ForecastConfig
        from mrr_forecast.data import CSVDataSource
        
        config = ForecastConfig(segments=['Basic', 'Pro', 'Enterprise'])
        data_source = CSVDataSource('./sample_data')
        
        forecaster = MRRForecaster(config, data_source)
        results = forecaster.run()
        
        print(results['mrr_summary'])
    """
    
    def __init__(
        self,
        config: ForecastConfig,
        data_source: DataSource,
        verbose: bool = True
    ):
        """
        Initialize the forecaster.
        
        Args:
            config: Forecast configuration
            data_source: Data source adapter
            verbose: Whether to print progress logs
        """
        self.config = config
        self.data_source = data_source
        self.logger = ForecastLogger(verbose=verbose)
        
        # Initialize models
        self.sub_forecaster = SubscriberForecaster(config, self.logger)
        self.arpc_forecaster = ARPCForecaster(config, self.logger)
        self.mrr_calculator = MRRCalculator(config, self.logger)
        
        # Results storage
        self._results: Dict[str, pd.DataFrame] = {}
    
    def run(self) -> Dict[str, pd.DataFrame]:
        """
        Run the full forecast pipeline.
        
        Returns:
            Dictionary with forecast results:
                - subscriber_forecast: Subscriber forecast by segment/age/cohort
                - arpc_forecast: ARPC forecast by segment/age/cohort
                - mrr_forecast: Full MRR forecast
                - mrr_summary: MRR summary by month and segment
                - mrr_total: Total MRR by month
        """
        self.logger.log_step("MRR Forecast Pipeline")
        self.logger.log(f"Base month: {self.config.base_month}")
        self.logger.log(f"Forecast horizon: {self.config.forecast_horizon_months} months")
        self.logger.log(f"Segments: {self.config.segments}")
        
        # Step 1: Load data
        self.logger.log_step("Loading Data")
        data = self._load_data()
        
        # Step 2: Subscriber forecast
        self.logger.log_step("Subscriber Forecast")
        sub_forecast = self.sub_forecaster.forecast(
            base_month_actuals=data['subscriber_history'],
            attrition_rates=data['attrition_rates'],
            gns_forecast=data['gns_forecast']
        )
        self._results['subscriber_forecast'] = sub_forecast
        
        # Step 3: ARPC forecast
        self.logger.log_step("ARPC Forecast")
        arpc_forecast = self.arpc_forecaster.forecast(
            base_month_arpc=data['arpc_history'],
            mom_change_rates=data['mom_change_rates'],
            age0_avg_arpc=data['age0_avg_arpc'],
            age26_avg_arpc=data['age26_avg_arpc'],
            overrides=data.get('arpc_overrides')
        )
        self._results['arpc_forecast'] = arpc_forecast
        
        # Step 4: Calculate MRR
        self.logger.log_step("MRR Calculation")
        mrr_forecast = self.mrr_calculator.calculate(sub_forecast, arpc_forecast)
        self._results['mrr_forecast'] = mrr_forecast
        
        # Step 5: Summarize
        self._results['mrr_summary'] = self.mrr_calculator.summarize(mrr_forecast)
        self._results['mrr_total'] = self.mrr_calculator.summarize_total(mrr_forecast)
        
        self.logger.log_step("Forecast Complete!")
        self.logger.log(f"Total forecast rows: {len(mrr_forecast):,}")
        
        return self._results
    
    def _load_data(self) -> Dict[str, pd.DataFrame]:
        """Load all required data from the data source."""
        data = {}
        
        # Load subscriber data
        self.logger.log("  Loading subscriber history...")
        sub_hist = self.data_source.get_subscriber_history()
        # Filter to base month for actuals
        sub_hist['month_begin'] = pd.to_datetime(sub_hist['month_begin'])
        base_month = pd.to_datetime(self.config.base_month)
        data['subscriber_history'] = sub_hist[sub_hist['month_begin'] == base_month]
        self.logger.log(f"    Loaded {len(data['subscriber_history']):,} rows")
        
        # Load attrition rates
        self.logger.log("  Loading attrition rates...")
        data['attrition_rates'] = self.data_source.get_attrition_rates()
        self.logger.log(f"    Loaded {len(data['attrition_rates']):,} rows")
        
        # Load GNS forecast
        self.logger.log("  Loading GNS forecast...")
        data['gns_forecast'] = self.data_source.get_gns_forecast()
        self.logger.log(f"    Loaded {len(data['gns_forecast']):,} rows")
        
        # Load ARPC data
        self.logger.log("  Loading ARPC history...")
        arpc_hist = self.data_source.get_arpc_history()
        arpc_hist['month_begin'] = pd.to_datetime(arpc_hist['month_begin'])
        data['arpc_history'] = arpc_hist[arpc_hist['month_begin'] == base_month]
        self.logger.log(f"    Loaded {len(data['arpc_history']):,} rows")
        
        # Calculate age 0 and age 26 averages
        data['age0_avg_arpc'] = self._calc_age0_avg(arpc_hist)
        data['age26_avg_arpc'] = self._calc_age26_avg(arpc_hist, base_month)
        
        # Load MoM rates
        self.logger.log("  Loading MoM change rates...")
        data['mom_change_rates'] = self.data_source.get_mom_change_rates()
        self.logger.log(f"    Loaded {len(data['mom_change_rates']):,} rows")
        
        # Load overrides (optional)
        self.logger.log("  Loading ARPC overrides...")
        data['arpc_overrides'] = self.data_source.get_arpc_overrides()
        if data['arpc_overrides'] is not None:
            self.logger.log(f"    Loaded {len(data['arpc_overrides']):,} overrides")
        else:
            self.logger.log("    No overrides found")
        
        return data
    
    def _calc_age0_avg(self, arpc_hist: pd.DataFrame) -> pd.DataFrame:
        """Calculate rolling average ARPC for age 0."""
        age0 = arpc_hist[arpc_hist['age'] == 0].copy()
        window = self.config.age0_arpc_rolling_window
        
        age0 = age0.sort_values(['segment', 'month_begin'])
        age0['age0_avg_arpc'] = age0.groupby('segment')['arpc'].transform(
            lambda x: x.rolling(window, min_periods=1).mean()
        )
        
        # Get latest value per segment
        result = age0.groupby('segment').last().reset_index()[['segment', 'age0_avg_arpc']]
        return result
    
    def _calc_age26_avg(self, arpc_hist: pd.DataFrame, base_month: pd.Timestamp) -> pd.DataFrame:
        """Calculate average ARPC for mature cohorts (age 26)."""
        age26 = arpc_hist[
            (arpc_hist['age'] == self.config.max_age) & 
            (arpc_hist['month_begin'] == base_month)
        ].copy()
        
        result = age26.groupby('segment')['arpc'].mean().reset_index()
        result.columns = ['segment', 'age26_avg_arpc']
        return result
    
    @property
    def results(self) -> Dict[str, pd.DataFrame]:
        """Get the latest forecast results."""
        return self._results
