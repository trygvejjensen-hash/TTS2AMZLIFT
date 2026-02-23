# TikTok → Amazon Sales Lift Dashboard

Measures incremental Amazon sales driven by TikTok activity using a rolling average baseline methodology.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## How It Works

1. **Baseline**: Rolling average of prior N months of Amazon sales per brand (default: 3 months)
2. **Lift**: `Actual Sales - Baseline Sales`
3. **Efficiency**: Lift ROAS, Cost per Lift Dollar, Lift per 1K Views/Impressions
4. **Confidence Flags**: High / Medium / Low / Inconclusive based on data quality and external events

## Data Format

Upload a CSV with these columns:

| Column | Required | Notes |
|---|---|---|
| `Brand` | ✅ | Brand name |
| `Month` | ✅ | YYYY-MM format |
| `Amazon_Sales` | ✅ | Total monthly Amazon revenue |
| `TikTok_Spend` | ✅ | Paid media spend |
| `TikTok_Impressions` | ✅ | From TikTok Ads Manager |
| `TikTok_Views` | ✅ | Video views |
| `TikTok_Engagements` | ✅ | Likes, shares, comments |
| `TikTok_Clicks` | ✅ | Click-throughs |
| `External_Event` | Optional | Prime Day, Holiday, etc. — flags lower confidence |

## File Structure

```
tts-amazon-lift/
├── app.py              # Streamlit dashboard
├── lift_engine.py      # Core calculation engine (importable)
├── sample_data.csv     # Test data (replace with your own)
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## Extending

- **Change baseline method**: Edit `compute_rolling_baseline()` in `lift_engine.py`
- **Add lag analysis**: Correlate TikTok metrics in week N with Amazon sales in weeks N+1, N+2, etc.
- **Add data sources**: Extend the CSV schema and update validation in `lift_engine.py`
