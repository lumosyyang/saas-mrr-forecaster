# Contributing to SaaS MRR Forecaster

Thank you for your interest in contributing to this project! This document provides guidelines and instructions for contributing.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Setup](#development-setup)
3. [Code Style](#code-style)
4. [Making Changes](#making-changes)
5. [Testing](#testing)
6. [Pull Request Process](#pull-request-process)
7. [Project Structure](#project-structure)

---

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- pip (Python package manager)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/saas-mrr-forecaster.git
   cd saas-mrr-forecaster
   ```

3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/lumosyyang/saas-mrr-forecaster.git
   ```

---

## Development Setup

### Create a Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### Install Dependencies

```bash
# Install package in development mode
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt
```

### Verify Installation

```bash
# Run the quickstart example
python examples/quickstart.py
```

---

## Code Style

### General Guidelines

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use meaningful variable and function names
- Add docstrings to all public functions and classes
- Keep functions focused and single-purpose
- Maximum line length: 100 characters

### Docstring Format

Use Google-style docstrings:

```python
def calculate_mrr(subscribers: pd.DataFrame, arpc: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Monthly Recurring Revenue.
    
    Args:
        subscribers: DataFrame with subscriber counts
            Required columns: month_begin, segment, age, open_subscriber
        arpc: DataFrame with ARPC values
            Required columns: month_begin, segment, age, arpc
    
    Returns:
        DataFrame with MRR calculations including:
            month_begin, segment, age, open_subscriber, arpc, mrr
    
    Raises:
        ValueError: If required columns are missing
    
    Example:
        >>> mrr_df = calculate_mrr(sub_df, arpc_df)
        >>> print(mrr_df['mrr'].sum())
    """
    ...
```

### Type Hints

Use type hints for function signatures:

```python
from typing import Optional, Dict, List
import pandas as pd

def forecast(
    base_data: pd.DataFrame,
    config: ForecastConfig,
    overrides: Optional[pd.DataFrame] = None
) -> Dict[str, pd.DataFrame]:
    ...
```

---

## Making Changes

### Branch Naming

Use descriptive branch names:

- `feature/add-spark-adapter` - New features
- `fix/arpc-calculation-bug` - Bug fixes
- `docs/update-readme` - Documentation updates
- `refactor/simplify-runner` - Code refactoring

### Commit Messages

Write clear, concise commit messages:

```
<type>: <short description>

<optional longer description>

<optional footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat: add Spark data source adapter

Implements SparkDataSource class that reads from Spark tables
and converts to Pandas DataFrames for processing.

Closes #15
```

```
fix: correct age-0 ARPC override logic

The override was not being applied when use_override_flag
was stored as a string. Added explicit type conversion.
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mrr_forecast

# Run specific test file
pytest tests/test_subscriber_forecast.py

# Run with verbose output
pytest -v
```

### Writing Tests

Place tests in the `tests/` directory:

```
tests/
├── __init__.py
├── test_config.py
├── test_subscriber_forecast.py
├── test_arpc_forecast.py
├── test_mrr_calculator.py
└── test_runner.py
```

Example test:

```python
import pytest
import pandas as pd
from mrr_forecast import ForecastConfig
from mrr_forecast.models import SubscriberForecaster

class TestSubscriberForecaster:
    
    @pytest.fixture
    def config(self):
        return ForecastConfig(
            segments=['Basic', 'Pro'],
            forecast_horizon_months=3
        )
    
    @pytest.fixture
    def sample_data(self):
        return pd.DataFrame({
            'month_begin': ['2025-12-01'] * 2,
            'segment': ['Basic', 'Pro'],
            'age': [0, 0],
            'cohort_month': ['2025-12-01'] * 2,
            'open_subscriber': [100, 50]
        })
    
    def test_forecast_creates_correct_months(self, config, sample_data):
        forecaster = SubscriberForecaster(config)
        # ... test implementation
```

---

## Pull Request Process

### Before Submitting

1. **Update your branch** with the latest upstream changes:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run tests** to ensure nothing is broken:
   ```bash
   pytest
   ```

3. **Update documentation** if you've changed functionality

4. **Add/update tests** for your changes

### Submitting a PR

1. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Open a Pull Request on GitHub

3. Fill out the PR template:
   - **Description**: What does this PR do?
   - **Related Issues**: Link any related issues
   - **Testing**: How was this tested?
   - **Checklist**: Confirm code style, tests, docs

### PR Review

- Respond to review comments promptly
- Make requested changes in new commits
- Once approved, squash and merge

---

## Project Structure

```
saas-mrr-forecaster/
├── mrr_forecast/                 # Main package
│   ├── __init__.py
│   ├── runner.py                 # Main orchestrator
│   ├── config/
│   │   └── model_config.py       # Configuration
│   ├── data/
│   │   ├── base.py               # Abstract data source
│   │   ├── csv_adapter.py        # CSV implementation
│   │   └── dataframe_adapter.py  # DataFrame implementation
│   ├── models/
│   │   ├── subscriber_forecast.py
│   │   ├── arpc_forecast.py
│   │   └── mrr_calculator.py
│   └── utils/
│       └── helpers.py
│
├── sample_data/                  # Example data files
├── examples/                     # Usage examples
├── tests/                        # Test files (to be added)
│
├── README.md
├── DOCUMENTATION.md
├── CONTRIBUTING.md               # This file
├── requirements.txt
└── setup.py
```

### Key Files to Know

| File | Purpose |
|------|---------|
| `runner.py` | Main entry point, orchestrates pipeline |
| `config/model_config.py` | All configuration parameters |
| `data/base.py` | Interface for data sources |
| `models/subscriber_forecast.py` | Subscriber count forecasting |
| `models/arpc_forecast.py` | Revenue per customer forecasting |
| `models/mrr_calculator.py` | Final MRR calculation |

---

## Adding New Features

### Adding a New Data Source

1. Create a new file in `mrr_forecast/data/`:
   ```python
   # mrr_forecast/data/spark_adapter.py
   from mrr_forecast.data.base import DataSource
   
   class SparkDataSource(DataSource):
       def __init__(self, spark, schema: str):
           self.spark = spark
           self.schema = schema
       
       def get_subscriber_history(self) -> pd.DataFrame:
           return self.spark.sql(f"SELECT * FROM {self.schema}.subscriber_history").toPandas()
       
       # ... implement other required methods
   ```

2. Export in `mrr_forecast/data/__init__.py`:
   ```python
   from mrr_forecast.data.spark_adapter import SparkDataSource
   ```

3. Add tests in `tests/test_spark_adapter.py`

4. Update documentation

### Adding a New Model

1. Create the model in `mrr_forecast/models/`
2. Follow the existing pattern (config injection, logger support)
3. Export in `mrr_forecast/models/__init__.py`
4. Integrate with `runner.py` if needed
5. Add comprehensive tests

---

## Questions?

If you have questions about contributing, feel free to:

1. Open an issue on GitHub
2. Check existing issues and discussions
3. Review the [DOCUMENTATION.md](DOCUMENTATION.md) for technical details

---

Thank you for contributing! 🎉
