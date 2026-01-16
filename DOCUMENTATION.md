# MRR-Forecast: Complete Documentation

> A comprehensive guide to the MRR (Monthly Recurring Revenue) Forecasting Package

---

## Table of Contents

1. [Package Overview](#1-package-overview)
2. [Architecture](#2-architecture)
3. [Configuration Module](#3-configuration-module)
4. [Data Layer](#4-data-layer)
5. [Utility Functions](#5-utility-functions)
6. [Core Models](#6-core-models)
   - [Subscriber Forecaster](#61-subscriber-forecaster)
   - [ARPC Forecaster](#62-arpc-forecaster)
   - [MRR Calculator](#63-mrr-calculator)
7. [Runner/Orchestrator](#7-runnerorchestrator)
8. [Data Flow](#8-data-flow)
9. [Key Formulas](#9-key-formulas)
10. [Extending the Package](#10-extending-the-package)

---

## 1. Package Overview

**MRR-Forecast** is a cohort-based revenue forecasting system that predicts Monthly Recurring Revenue by:

1. **Forecasting subscriber counts** using attrition rates and GNS (Gross New Subscribers) projections
2. **Forecasting ARPC** (Average Revenue Per Customer) using month-over-month change rates
3. **Calculating MRR** as the product of subscribers × ARPC

### Key Concepts

| Term | Definition |
|------|------------|
| **MRR** | Monthly Recurring Revenue = Subscribers × ARPC |
| **GNS** | Gross New Subscribers - new customers acquired in a month |
| **ARPC** | Average Revenue Per Customer |
| **Age** | Months since a customer's GNS (0 = first month) |
| **Cohort** | Group of customers who subscribed in the same month |
| **Segment** | Business category (e.g., Basic, Pro, Enterprise) |
| **T0** | Base month - the last complete month with actual data |

---

## 2. Architecture

```
mrr-forecast/
├── mrr_forecast/
│   ├── config/                  # ① Configuration
│   │   ├── __init__.py
│   │   └── model_config.py      # ForecastConfig dataclass
│   │
│   ├── data/                    # ② Data Layer (Abstraction)
│   │   ├── __init__.py
│   │   ├── base.py              # Abstract DataSource class
│   │   ├── csv_adapter.py       # CSV file implementation
│   │   └── dataframe_adapter.py # DataFrame implementation
│   │
│   ├── utils/                   # ③ Utilities
│   │   ├── __init__.py
│   │   └── helpers.py           # Date functions, logging
│   │
│   ├── models/                  # ④ Core Algorithms
│   │   ├── __init__.py
│   │   ├── subscriber_forecast.py
│   │   ├── arpc_forecast.py
│   │   └── mrr_calculator.py
│   │
│   ├── __init__.py
│   └── runner.py                # ⑤ Orchestrator
│
├── sample_data/                 # Example data files
├── examples/                    # Usage examples
├── requirements.txt
├── setup.py
└── README.md
```

### Design Principles

1. **Separation of Concerns**: Each module has a single responsibility
2. **Dependency Injection**: Data sources are injected, not hardcoded
3. **Configuration as Code**: All parameters in one place
4. **Testability**: Pure functions where possible, clear interfaces

---

## 3. Configuration Module

**File**: `mrr_forecast/config/model_config.py`

**Purpose**: Single source of truth for all model parameters.

### ForecastConfig Dataclass

```python
from dataclasses import dataclass, field
from datetime import date
from typing import List

@dataclass
class ForecastConfig:
    """Configuration for the MRR forecasting model."""
    
    # ═══════════════════════════════════════════════════════════
    # SEGMENT DEFINITIONS
    # ═══════════════════════════════════════════════════════════
    segments: List[str] = field(default_factory=lambda: [
        'Basic',
        'Pro',
        'Enterprise',
        'Mobile',
    ])
    
    # ═══════════════════════════════════════════════════════════
    # DATE CONFIGURATION
    # ═══════════════════════════════════════════════════════════
    base_date: date              # Reference date (default: today)
    base_month_offset: int = -1  # T0 = last completed month
    forecast_horizon_months: int = 15
    historical_lookback_months: int = 12
    
    # ═══════════════════════════════════════════════════════════
    # AGE COHORT CONFIGURATION
    # ═══════════════════════════════════════════════════════════
    min_age: int = 0
    max_age: int = 26            # Customers older than this are bucketed
    mature_cohort_date: str = '2099-01-01'  # Placeholder for mature cohorts
    
    # ═══════════════════════════════════════════════════════════
    # ARPC CONFIGURATION
    # ═══════════════════════════════════════════════════════════
    enable_arpc_overrides: bool = True
    age0_arpc_rolling_window: int = 4  # Months for rolling average
    early_life_ages: List[int] = field(default_factory=lambda: [0, 1, 2, 3])
```

### Key Computed Properties

```python
@property
def base_month(self) -> date:
    """
    T0: The last complete month before forecasting starts.
    
    Example:
        base_date = January 15, 2026
        base_month_offset = -1
        → base_month = December 1, 2025
    """
    ref = self.base_date.replace(day=1)  # First of month
    return ref + relativedelta(months=self.base_month_offset)

@property
def forecast_end_month(self) -> date:
    """Last month of the forecast period."""
    return self.base_month + relativedelta(months=self.forecast_horizon_months)

@property
def historical_start(self) -> date:
    """Start date for historical rate calculations."""
    return self.base_month + relativedelta(months=-self.historical_lookback_months)
```

### Why These Defaults?

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| `max_age` | 26 | After ~2 years, customer behavior stabilizes |
| `base_month_offset` | -1 | Forecast from most recently completed month |
| `age0_arpc_rolling_window` | 4 | 4-month average smooths monthly fluctuations |
| `forecast_horizon_months` | 15 | Common planning horizon (current FY + next) |

### Usage Example

```python
from datetime import date
from mrr_forecast import ForecastConfig

# Custom configuration
config = ForecastConfig(
    segments=['Starter', 'Growth', 'Scale'],
    base_date=date(2026, 1, 15),
    base_month_offset=-1,           # T0 = Dec 2025
    forecast_horizon_months=18,     # 18-month forecast
    max_age=30,                     # Track up to 30 months
)

print(f"Base month: {config.base_month}")           # 2025-12-01
print(f"Forecast end: {config.forecast_end_month}") # 2027-06-01
```

---

## 4. Data Layer

**Files**: `mrr_forecast/data/`

**Purpose**: Abstract away data sources. Works with CSV, databases, Spark, or any data store.

### 4.1 Abstract Base Class (`base.py`)

```python
from abc import ABC, abstractmethod
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
            - net_attrition: float (net change from attrition)
            - migrate_in: float (subscribers migrating in)
            - migrate_out: float (subscribers migrating out)
        """
        pass
    
    @abstractmethod
    def get_attrition_rates(self) -> pd.DataFrame:
        """
        Get historical attrition/migration rates by segment and age.
        
        Required columns:
            - segment: str
            - age: int
            - median_attrition_rate: float
            - median_inflow_rate: float
            - median_outflow_rate: float
        """
        pass
    
    @abstractmethod
    def get_gns_forecast(self) -> pd.DataFrame:
        """
        Get forecasted Gross New Subscribers by segment and month.
        
        Required columns:
            - month_begin: date
            - segment: str
            - new_subscriber_fcst: float
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
            - arpc: float
        """
        pass
    
    @abstractmethod
    def get_mom_change_rates(self) -> pd.DataFrame:
        """
        Get month-over-month ARPC change rates.
        
        Required columns:
            - segment: str
            - age: int
            - avg_mom_pct_change: float
        """
        pass
    
    def get_arpc_overrides(self) -> Optional[pd.DataFrame]:
        """
        Get manual ARPC overrides (optional).
        
        Required columns if provided:
            - segment: str
            - cohort_month: date
            - age0_arpc_manual: float
            - mom_0_to_1_manual_pct: float
            - mom_1_to_2_manual_pct: float
            - mom_2_to_3_manual_pct: float
            - use_override_flag: int (1 to use, 0 to skip)
        """
        return None
```

### 4.2 CSV Implementation (`csv_adapter.py`)

```python
class CSVDataSource(DataSource):
    """
    Load forecast input data from CSV files.
    
    Expected files in data_dir:
        - subscriber_history.csv
        - attrition_rates.csv
        - gns_forecast.csv
        - arpc_history.csv
        - mom_change_rates.csv
        - arpc_overrides.csv (optional)
    """
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
    
    def get_subscriber_history(self) -> pd.DataFrame:
        return pd.read_csv(
            f'{self.data_dir}/subscriber_history.csv',
            parse_dates=['month_begin', 'cohort_month']
        )
    
    # ... other methods follow similar pattern
```

### 4.3 DataFrame Implementation (`dataframe_adapter.py`)

For in-memory data or Spark DataFrames converted to Pandas:

```python
class DataFrameSource(DataSource):
    """
    Load data directly from Pandas DataFrames.
    
    Useful for:
        - Testing with mock data
        - Integration with Spark (convert to Pandas)
        - Dynamic data generation
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
        self._subscriber_history = subscriber_history
        self._attrition_rates = attrition_rates
        # ... store all dataframes
```

### Why Abstract?

The abstraction allows you to swap data sources without changing model code:

```python
# Development: CSV files
data_source = CSVDataSource('./sample_data')

# Production: Databricks/Spark
data_source = SparkDataSource(spark, schema='analytics')

# Testing: In-memory DataFrames
data_source = DataFrameSource(mock_subs, mock_rates, ...)

# Same model code works with any source!
forecaster = MRRForecaster(config, data_source)
```

---

## 5. Utility Functions

**File**: `mrr_forecast/utils/helpers.py`

### Date Functions

```python
from datetime import date
from dateutil.relativedelta import relativedelta

def add_months(d: date, months: int) -> date:
    """
    Add or subtract months from a date.
    
    Args:
        d: Base date
        months: Number of months (can be negative)
    
    Returns:
        New date with months added
    
    Example:
        add_months(date(2025, 1, 15), 3)  → date(2025, 4, 15)
        add_months(date(2025, 1, 15), -1) → date(2024, 12, 15)
    """
    if isinstance(d, pd.Timestamp):
        d = d.date()
    return d + relativedelta(months=months)

def first_of_month(d: date) -> date:
    """
    Normalize date to first day of month.
    
    Example:
        first_of_month(date(2025, 3, 15)) → date(2025, 3, 1)
    """
    return d.replace(day=1)
```

### Logging

```python
class ForecastLogger:
    """Simple logger for forecast progress."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
    
    def log(self, message: str):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[MRR-Forecast] {message}")
    
    def log_step(self, step_name: str):
        """Log a major step with visual separator."""
        self.log(f"\n{'='*60}")
        self.log(f"  {step_name}")
        self.log(f"{'='*60}")
    
    def log_result(self, table_name: str, row_count: int):
        """Log result creation."""
        self.log(f"  Created: {table_name} ({row_count:,} rows)")
```

---

## 6. Core Models

### 6.1 Subscriber Forecaster

**File**: `mrr_forecast/models/subscriber_forecast.py`

**Purpose**: Forecast subscriber counts by segment and age cohort.

#### Algorithm Overview

```
For each forecast month T1, T2, ... Tn:
│
├── Age 0 (New Cohort):
│   └── new_subscriber = GNS forecast for this segment/month
│
├── Age 1-25 (Rolling Forward):
│   └── prior_subs = last month's open_subscriber at (age - 1)
│       open_subscriber = prior_subs × (1 + attrition + inflow + outflow)
│
└── Age 26 (Mature Bucket):
    └── prior_subs = last month's (age 25) + (age 26)
        open_subscriber = prior_subs × (1 + rates...)
```

#### Class Structure

```python
class SubscriberForecaster:
    """
    Forecasts subscriber counts by segment and age cohort.
    
    Uses cohort-based modeling with:
    - Historical attrition rates
    - Migration flows between segments
    - GNS (Gross New Subscriber) forecasts for age 0
    """
    
    def __init__(self, config: ForecastConfig, logger: ForecastLogger = None):
        self.config = config
        self.logger = logger or ForecastLogger(verbose=False)
    
    def forecast(
        self,
        base_month_actuals: pd.DataFrame,  # T0 actual subscribers
        attrition_rates: pd.DataFrame,      # Median rates by segment/age
        gns_forecast: pd.DataFrame          # GNS forecast by segment/month
    ) -> pd.DataFrame:
        """Generate subscriber forecast."""
        ...
```

#### Key Method: `_forecast_one_month()`

```python
def _forecast_one_month(self, current_df, rates_df, gns_df, forecast_month):
    """Forecast one month forward."""
    
    max_age = self.config.max_age
    mature_date = pd.to_datetime(self.config.mature_cohort_date)
    
    # 1. SHIFT TIME FORWARD
    # ─────────────────────────────────────────────────────────
    tN = current_df.copy()
    tN['month_begin'] = forecast_month
    tN['cohort_month'] = tN['cohort_month'].apply(
        lambda x: x if x == mature_date else x + pd.DateOffset(months=1)
    )
    
    # 2. GET GNS FOR THIS MONTH
    # ─────────────────────────────────────────────────────────
    gns_this_month = gns_df[gns_df['month_begin'] == forecast_month]
    tN = tN.merge(
        gns_this_month[['segment', 'new_subscriber_fcst']],
        on='segment', how='left'
    )
    
    # 3. MERGE ATTRITION RATES
    # ─────────────────────────────────────────────────────────
    tN = tN.merge(rates_df, on=['segment', 'age'], how='left')
    
    # 4. CALCULATE PRIOR_SUBS (who rolls into this age)
    # ─────────────────────────────────────────────────────────
    for segment in tN['segment'].unique():
        for age in range(0, max_age + 1):
            
            if age == 0:
                # New subscribers from GNS forecast
                prior_subs = gns_forecast_value
                
            elif age == max_age:
                # Mature bucket: accumulate from age-1 AND age-26
                prior_subs = (age_25_subs) + (age_26_subs)
                
            else:
                # Standard: roll from prior age
                prior_subs = last_month[age - 1].open_subscriber
    
    # 5. APPLY RATES
    # ─────────────────────────────────────────────────────────
    tN['net_attrition'] = prior_subs × median_attrition_rate
    tN['migrate_in'] = prior_subs × median_inflow_rate
    tN['migrate_out'] = prior_subs × median_outflow_rate
    
    # 6. CALCULATE OPEN_SUBSCRIBER
    # ─────────────────────────────────────────────────────────
    tN['open_subscriber'] = (
        prior_subs 
        + net_attrition 
        + migrate_in 
        + migrate_out
    )
    
    return tN
```

#### Visual Example

```
        Base Month (T0)                     Forecast (T1)
    ┌───────────────────┐               ┌───────────────────┐
Age │   Subscribers     │               │   Subscribers     │
────┼───────────────────┤               ├───────────────────┤
  0 │      100          │  ──GNS───→    │      120 (new)    │
  1 │       85          │  ──roll──→    │  100 × 0.92 = 92  │
  2 │       78          │  ──roll──→    │   85 × 0.94 = 80  │
  3 │       72          │  ──roll──→    │   78 × 0.95 = 74  │
... │       ...         │               │       ...         │
 25 │       45          │  ──roll──→    │   48 × 0.97 = 47  │
 26 │      500          │  ──bucket──→  │ (45+500) × 0.98   │
    └───────────────────┘               └───────────────────┘
```

#### Rate Meanings

| Rate | Definition | Typical Values |
|------|------------|----------------|
| `median_attrition_rate` | Net subscriber loss (negative) | -0.02 to -0.08 |
| `median_inflow_rate` | Migration from other segments | 0.001 to 0.01 |
| `median_outflow_rate` | Migration to other segments (negative) | -0.001 to -0.01 |

---

### 6.2 ARPC Forecaster

**File**: `mrr_forecast/models/arpc_forecast.py`

**Purpose**: Forecast ARPC (Average Revenue Per Customer) by segment and age.

#### Algorithm Overview

```
For each forecast month:
│
├── Age 0 (New Cohort):
│   ├── Check for manual override (age0_arpc_manual)
│   └── Else: Use 4-month rolling average ARPC
│
├── Age 1-3 (Early Life):
│   ├── Check for manual MoM override (mom_0_to_1_manual_pct, etc.)
│   └── Apply: ARPC = prior_arpc × (1 + mom_rate)
│
├── Age 4-25 (Standard):
│   └── ARPC = prior_arpc × (1 + avg_mom_pct_change)
│
└── Age 26 (Mature):
    └── ARPC = age26_avg_arpc (capped at historical average)
```

#### Class Structure

```python
class ARPCForecaster:
    """
    Forecasts ARPC by segment and age cohort.
    
    Uses MoM (month-over-month) change rates with:
    - Age 0: Rolling average or manual overrides
    - Age 26+: Capped at mature cohort average
    """
    
    def forecast(
        self,
        base_month_arpc: pd.DataFrame,     # T0 actual ARPC
        mom_change_rates: pd.DataFrame,    # MoM % change rates
        age0_avg_arpc: pd.DataFrame,       # Rolling avg for age 0
        age26_avg_arpc: pd.DataFrame,      # Historical avg for age 26
        overrides: Optional[pd.DataFrame]  # Manual overrides
    ) -> pd.DataFrame:
        """Generate ARPC forecast."""
        ...
```

#### Key Method: `_calc_arpc()`

```python
def _calc_arpc(self, row, overrides, max_age):
    """
    Calculate ARPC for a single row.
    
    Decision tree:
        Age 0 → Manual override OR rolling average
        Age 1-3 → Manual MoM override OR standard MoM
        Age 4-25 → Standard MoM rate
        Age 26 → Historical average (capped)
    """
    age = row['age']
    segment = row['segment']
    cohort = row['cohort_month']
    prior_arpc = row['prior_arpc']
    mom_rate = row['avg_mom_pct_change']
    
    # ═══════════════════════════════════════════════════════════
    # AGE 0: NEW INTAKE
    # ═══════════════════════════════════════════════════════════
    if age == 0:
        # Check for manual override first
        if overrides is not None:
            override = overrides[
                (overrides['segment'] == segment) & 
                (overrides['cohort_month'] == cohort)
            ]
            if not override.empty:
                manual = override['age0_arpc_manual'].iloc[0]
                if pd.notna(manual):
                    return manual
        
        # Fall back to rolling average
        return row.get('age0_avg_arpc', prior_arpc)
    
    # ═══════════════════════════════════════════════════════════
    # AGE 26: MATURE COHORT (CAPPED)
    # ═══════════════════════════════════════════════════════════
    if age == max_age:
        return row.get('age26_avg_arpc', prior_arpc)
    
    # ═══════════════════════════════════════════════════════════
    # AGE 1-3: CHECK FOR MANUAL MOM OVERRIDE
    # ═══════════════════════════════════════════════════════════
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
    
    # ═══════════════════════════════════════════════════════════
    # APPLY MOM RATE
    # ═══════════════════════════════════════════════════════════
    return prior_arpc * (1 + mom_rate)
```

#### Why Special Handling by Age?

| Age | Special Treatment | Rationale |
|-----|-------------------|-----------|
| **0** | Manual override OR rolling average | New cohorts have no history; pricing may be promotional |
| **1-3** | Manual MoM override | Early life is volatile (promos expire, upgrades); allow manual adjustment |
| **4-25** | Standard MoM rates | Stable period; historical patterns are reliable |
| **26** | Capped at historical average | Mature cohorts stabilize; prevents runaway growth |

#### MoM Rate Explanation

```
MoM (Month-over-Month) Rate represents average price change as customers age.

Example:
  - MoM rate = 0.02 (2%)
  - Prior ARPC: $50.00
  - New ARPC: $50.00 × (1 + 0.02) = $51.00

This captures:
  ✓ Price increases
  ✓ Discount expirations (intro pricing ends)
  ✓ Plan upgrades (Basic → Pro)
  ✓ Add-on purchases
```

#### Override Structure

```csv
segment,cohort_month,age0_arpc_manual,mom_0_to_1_manual_pct,mom_1_to_2_manual_pct,mom_2_to_3_manual_pct,use_override_flag
Basic,2026-01-01,25.00,0.05,0.03,0.02,1
Pro,2026-01-01,75.00,0.04,0.02,0.01,1
```

---

### 6.3 MRR Calculator

**File**: `mrr_forecast/models/mrr_calculator.py`

**Purpose**: Multiply subscribers × ARPC to get MRR.

#### Formula

```
MRR = Open Subscribers × ARPC
```

#### Class Structure

```python
class MRRCalculator:
    """
    Calculates Monthly Recurring Revenue from subscriber and ARPC forecasts.
    """
    
    def calculate(
        self,
        subscriber_forecast: pd.DataFrame,
        arpc_forecast: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate MRR from forecasts.
        
        Joins on: month_begin, segment, age, cohort_month
        """
        # Merge forecasts
        mrr_df = subscriber_forecast.merge(
            arpc_forecast[['month_begin', 'segment', 'age', 'cohort_month', 'arpc']],
            on=['month_begin', 'segment', 'age', 'cohort_month'],
            how='left'
        )
        
        # Calculate MRR
        mrr_df['mrr'] = mrr_df['open_subscriber'] * mrr_df['arpc']
        
        return mrr_df
    
    def summarize(self, mrr_forecast, group_by=['month_begin', 'segment']):
        """Aggregate MRR by specified dimensions."""
        summary = mrr_forecast.groupby(group_by).agg({
            'open_subscriber': 'sum',
            'mrr': 'sum'
        }).reset_index()
        
        # Calculate implied ARPC
        summary['arpc'] = summary['mrr'] / summary['open_subscriber']
        return summary
    
    def summarize_total(self, mrr_forecast):
        """Get total MRR by month (across all segments)."""
        return self.summarize(mrr_forecast, group_by=['month_begin'])
```

---

## 7. Runner/Orchestrator

**File**: `mrr_forecast/runner.py`

**Purpose**: Orchestrate the full pipeline in correct order.

### MRRForecaster Class

```python
class MRRForecaster:
    """
    Main class to orchestrate the full MRR forecasting pipeline.
    
    Pipeline:
        1. Load data from DataSource
        2. Run subscriber forecast
        3. Run ARPC forecast
        4. Calculate MRR = Subscribers × ARPC
    """
    
    def __init__(
        self,
        config: ForecastConfig,
        data_source: DataSource,
        verbose: bool = True
    ):
        self.config = config
        self.data_source = data_source
        self.logger = ForecastLogger(verbose=verbose)
        
        # Initialize all three models
        self.sub_forecaster = SubscriberForecaster(config, self.logger)
        self.arpc_forecaster = ARPCForecaster(config, self.logger)
        self.mrr_calculator = MRRCalculator(config, self.logger)
```

### run() Method - The Full Pipeline

```python
def run(self) -> Dict[str, pd.DataFrame]:
    """
    Run the full forecast pipeline.
    
    Returns:
        Dictionary with:
            - subscriber_forecast: Full detail
            - arpc_forecast: Full detail
            - mrr_forecast: Full detail with MRR
            - mrr_summary: By month and segment
            - mrr_total: By month only
    """
    self.logger.log_step("MRR Forecast Pipeline")
    
    # ═══════════════════════════════════════════════════════════
    # STEP 1: LOAD DATA
    # ═══════════════════════════════════════════════════════════
    self.logger.log_step("Loading Data")
    data = self._load_data()
    
    # ═══════════════════════════════════════════════════════════
    # STEP 2: SUBSCRIBER FORECAST
    # ═══════════════════════════════════════════════════════════
    self.logger.log_step("Subscriber Forecast")
    sub_forecast = self.sub_forecaster.forecast(
        base_month_actuals=data['subscriber_history'],
        attrition_rates=data['attrition_rates'],
        gns_forecast=data['gns_forecast']
    )
    
    # ═══════════════════════════════════════════════════════════
    # STEP 3: ARPC FORECAST
    # ═══════════════════════════════════════════════════════════
    self.logger.log_step("ARPC Forecast")
    arpc_forecast = self.arpc_forecaster.forecast(
        base_month_arpc=data['arpc_history'],
        mom_change_rates=data['mom_change_rates'],
        age0_avg_arpc=data['age0_avg_arpc'],
        age26_avg_arpc=data['age26_avg_arpc'],
        overrides=data.get('arpc_overrides')
    )
    
    # ═══════════════════════════════════════════════════════════
    # STEP 4: CALCULATE MRR
    # ═══════════════════════════════════════════════════════════
    self.logger.log_step("MRR Calculation")
    mrr_forecast = self.mrr_calculator.calculate(sub_forecast, arpc_forecast)
    
    # ═══════════════════════════════════════════════════════════
    # STEP 5: SUMMARIZE
    # ═══════════════════════════════════════════════════════════
    mrr_summary = self.mrr_calculator.summarize(mrr_forecast)
    mrr_total = self.mrr_calculator.summarize_total(mrr_forecast)
    
    return {
        'subscriber_forecast': sub_forecast,
        'arpc_forecast': arpc_forecast,
        'mrr_forecast': mrr_forecast,
        'mrr_summary': mrr_summary,
        'mrr_total': mrr_total
    }
```

### Data Loading

```python
def _load_data(self) -> Dict[str, pd.DataFrame]:
    """Load all required data from the data source."""
    data = {}
    
    # Load subscriber history and filter to base month
    sub_hist = self.data_source.get_subscriber_history()
    base_month = pd.to_datetime(self.config.base_month)
    data['subscriber_history'] = sub_hist[sub_hist['month_begin'] == base_month]
    
    # Load rates and forecasts
    data['attrition_rates'] = self.data_source.get_attrition_rates()
    data['gns_forecast'] = self.data_source.get_gns_forecast()
    
    # Load ARPC data and filter to base month
    arpc_hist = self.data_source.get_arpc_history()
    data['arpc_history'] = arpc_hist[arpc_hist['month_begin'] == base_month]
    
    # Calculate derived inputs
    data['age0_avg_arpc'] = self._calc_age0_avg(arpc_hist)
    data['age26_avg_arpc'] = self._calc_age26_avg(arpc_hist, base_month)
    
    # Load MoM rates and optional overrides
    data['mom_change_rates'] = self.data_source.get_mom_change_rates()
    data['arpc_overrides'] = self.data_source.get_arpc_overrides()
    
    return data
```

---

## 8. Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              INPUT DATA                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  subscriber_history.csv   →  T0 actuals (segment, age, open_subs)       │
│  attrition_rates.csv      →  Median rates (attrition, in/out flow)      │
│  gns_forecast.csv         →  GNS by segment/month                       │
│  arpc_history.csv         →  T0 ARPC (segment, age, arpc)               │
│  mom_change_rates.csv     →  MoM % change by segment/age                │
│  arpc_overrides.csv       →  Manual overrides (optional)                │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         RUNNER (MRRForecaster)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌──────────────────────────┐    ┌──────────────────────────┐          │
│   │  SubscriberForecaster    │    │  ARPCForecaster          │          │
│   │                          │    │                          │          │
│   │  T0 → T1 → T2 → ... → Tn │    │  T0 → T1 → T2 → ... → Tn │          │
│   │                          │    │                          │          │
│   │  Output: open_subscriber │    │  Output: arpc            │          │
│   └─────────────┬────────────┘    └─────────────┬────────────┘          │
│                 │                               │                       │
│                 └───────────────┬───────────────┘                       │
│                                 │                                       │
│                                 ▼                                       │
│                  ┌──────────────────────────┐                           │
│                  │     MRRCalculator        │                           │
│                  │                          │                           │
│                  │  MRR = subs × ARPC       │                           │
│                  └─────────────┬────────────┘                           │
│                                │                                        │
└────────────────────────────────┼────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              OUTPUT                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  subscriber_forecast   →  Full detail (segment, age, cohort, month)     │
│  arpc_forecast        →  Full detail (segment, age, cohort, month)      │
│  mrr_forecast         →  Full detail with MRR calculated                │ 
│  mrr_summary          →  Aggregated by month + segment                  │ 
│  mrr_total            →  Aggregated by month only                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Key Formulas

### Subscriber Formulas

| Metric | Formula | Notes |
|--------|---------|-------|
| **Open Subscribers (age 0)** | `GNS_forecast` | New subscribers from external forecast |
| **Open Subscribers (age 1-25)** | `prior_age_subs × (1 + attrition + inflow + outflow)` | Roll forward with rates |
| **Open Subscribers (age 26)** | `(age25 + age26) × (1 + attrition + ...)` | Mature bucket accumulates |

### ARPC Formulas

| Metric | Formula | Notes |
|--------|---------|-------|
| **ARPC (age 0)** | `manual_override` OR `rolling_4mo_avg` | Override takes priority |
| **ARPC (age 1-3)** | `prior_arpc × (1 + manual_mom)` OR `prior_arpc × (1 + avg_mom)` | Override for early life |
| **ARPC (age 4-25)** | `prior_arpc × (1 + avg_mom_pct_change)` | Standard rollforward |
| **ARPC (age 26)** | `age26_historical_avg` | Capped at mature average |

### MRR Formula

```
MRR = Σ (open_subscriber[s,a,c] × arpc[s,a,c])

Where:
  s = segment
  a = age
  c = cohort
```

---

## 10. Extending the Package

### Adding a New Data Source

```python
from mrr_forecast.data.base import DataSource
import pandas as pd

class SparkDataSource(DataSource):
    """Load data from Spark tables."""
    
    def __init__(self, spark, schema: str):
        self.spark = spark
        self.schema = schema
    
    def get_subscriber_history(self) -> pd.DataFrame:
        return self.spark.sql(f"""
            SELECT * FROM {self.schema}.subscriber_history
        """).toPandas()
    
    # ... implement other methods
```

### Adding a New Segment

Simply add to the config:

```python
config = ForecastConfig(
    segments=['Basic', 'Pro', 'Enterprise', 'NewPlan'],  # Added NewPlan
    ...
)
```

### Customizing ARPC Logic

Subclass `ARPCForecaster`:

```python
class CustomARPCForecaster(ARPCForecaster):
    def _calc_arpc(self, row, overrides, max_age):
        # Your custom logic here
        if row['segment'] == 'Enterprise':
            # Custom handling for Enterprise
            return self._enterprise_arpc(row)
        
        # Default behavior
        return super()._calc_arpc(row, overrides, max_age)
```

---

## Appendix: Sample Data Schemas

### subscriber_history.csv

```csv
month_begin,segment,age,cohort_month,open_subscriber,new_subscriber,net_attrition,migrate_in,migrate_out
2025-12-01,Basic,0,2025-12-01,385.12,385.12,-30.81,3.85,-3.85
2025-12-01,Basic,1,2025-11-01,327.35,0,-22.27,3.27,-3.27
```

### attrition_rates.csv

```csv
segment,age,median_attrition_rate,median_inflow_rate,median_outflow_rate
Basic,0,-0.08,0.01,-0.01
Basic,1,-0.068,0.01,-0.01
```

### gns_forecast.csv

```csv
month_begin,segment,new_subscriber_fcst
2026-01-01,Basic,400.5
2026-01-01,Pro,150.25
```

### arpc_history.csv

```csv
month_begin,segment,age,cohort_month,arpc
2025-12-01,Basic,0,2025-12-01,15.50
2025-12-01,Basic,1,2025-11-01,16.25
```

### mom_change_rates.csv

```csv
segment,age,avg_mom_pct_change
Basic,0,0.0
Basic,1,0.02
Basic,2,0.015
```

### arpc_overrides.csv

```csv
segment,cohort_month,age0_arpc_manual,mom_0_to_1_manual_pct,mom_1_to_2_manual_pct,mom_2_to_3_manual_pct,use_override_flag
Basic,2026-01-01,16.00,0.03,0.02,0.015,1
Pro,2026-01-01,45.00,0.025,0.018,0.012,1
```

---

*Last updated: January 2026*
