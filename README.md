# MRR Forecast

**A modular, open-source framework for forecasting Monthly Recurring Revenue (MRR) using cohort-based subscriber and ARPC modeling.**

Perfect for SaaS companies that want to forecast revenue by customer segment, age cohort, and subscription tenure.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the demo
python examples/quickstart.py
```

## 📊 What This Does

This framework forecasts MRR using a three-stage approach:

1. **Open Subscriber Forecast** - Predicts future subscriber counts by segment and age cohort using historical attrition, inflow, and outflow rates
2. **ARPC Forecast** - Predicts Average Revenue Per Customer using month-over-month change rates and discount expiration dynamics
3. **MRR Calculation** - Combines forecasts: `MRR = Open Subscribers × ARPC`

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Historical     │     │  GNS Forecast   │     │  ARPC History   │
│  Subscribers    │     │  (New Subs)     │     │  & MoM Rates    │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MRR Forecast Engine                         │
├─────────────────┬─────────────────┬─────────────────────────────┤
│ Subscriber      │ ARPC            │ MRR                         │
│ Forecast        │ Forecast        │ Calculator                  │
│ (by cohort/age) │ (by cohort/age) │ (Subs × ARPC)              │
└─────────────────┴─────────────────┴─────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Output: MRR Forecast by Month, Segment, Age Cohort             │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
mrr-forecast/
├── mrr_forecast/              # Core package
│   ├── config/                # Configuration
│   ├── data/                  # Data adapters
│   ├── models/                # Forecasting algorithms
│   └── utils/                 # Helper functions
├── sample_data/               # Synthetic datasets
├── examples/                  # Usage examples
└── tests/                     # Unit tests
```

## 🔧 Configuration

Edit `mrr_forecast/config/model_config.py` to customize:

- **Segments**: Define your product tiers (Basic, Pro, Enterprise, etc.)
- **Age Cohorts**: Set maximum tracking age (default: 26 months)
- **Forecast Horizon**: How many months to forecast (default: 15)
- **Historical Lookback**: Months of history for rate calculations (default: 12)

## 📈 Core Concepts

### Segments
Customer groups you want to track separately (e.g., by product tier, channel, region).

### Age Cohorts
Months since a customer's first subscription (GNS = Gross New Subscription month).
- Age 0: GNS month
- Age 1: First month after GNS
- Age 26+: Mature cohort (grouped together)

### Key Metrics
- **Attrition Rate**: % of subscribers who cancel each month
- **Inflow Rate**: % migrating INTO a segment from another
- **Outflow Rate**: % migrating OUT of a segment to another
- **MoM Change**: Month-over-month ARPC change (driven by price changes, discount expirations)

## 🎯 Use Cases

- Quarterly/annual revenue forecasting
- Scenario planning (what-if analysis)
- Understanding cohort behavior
- Pricing impact analysis

## 📝 License

MIT License - feel free to use, modify, and distribute.

## 🤝 Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.
