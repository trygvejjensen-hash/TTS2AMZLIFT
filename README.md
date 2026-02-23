# TTS → Amazon Lift Model

**Pattern × NextWave** — Data-driven attribution model measuring TikTok Shop's impact on Amazon sales.

## What This Does

Upload your monthly Broadway Tool (XLSM) and Amazon Report (XLSX) and the app automatically:
- Calculates Pearson correlation between TTS GMV and Amazon sales (monthly, with lag analysis)
- Sets brand-specific attribution rates based on correlation strength
- Applies a 4x GMV cap to prevent over-attribution  
- Shows the full TTS content funnel (impressions → visitors → videos → GMV)
- Generates confidence scores per brand

## Quick Start

1. Install requirements: `pip install -r requirements.txt`
2. Run: `streamlit run app.py`
3. Upload your Broadway Tool in the sidebar
4. (Optional) Upload the Amazon monthly report for full correlation

## Deployment

This app is deployed on [Streamlit Cloud](https://share.streamlit.io). 

## Monthly Workflow

1. Export the Broadway Tool XLSM from NextWave
2. Export the Amazon Broadway report XLSX
3. Upload both files in the sidebar
4. Review updated attribution and download CSV

## Model Methodology

| Correlation (r) | Attribution Rate | Confidence |
|:---:|:---:|:---:|
| r ≥ 0.8 | 17% | HIGH |
| r ≥ 0.5 | 12% | MED |
| r ≥ 0.3 | 6% | LOW |
| r < 0.3 | 2% | WEAK |
| < 3 months | 3% | INSUF |

**Cap Rule:** Attributed AMZ Sales = min(AMZ Sales × Rate, TTS GMV × 4)
