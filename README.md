# TTS → Amazon Lift Model v6

**YoY Pre/Post Attribution with 2024 Baseline**

## How It Works

This model measures TikTok Shop's impact on Amazon organic sales by comparing 2025 performance against embedded 2024 baselines.

### Attribution Waterfall
1. **Organic Δ YoY** — Same-month comparison (Jan '25 vs Jan '24, etc.) controls for seasonality
2. **Ad Halo Discount** — If Amazon ad spend grew, 25% of that growth is assumed to spill over into organic. Subtracted.
3. **Unexplained Organic** — Growth not explained by ad spend changes
4. **TTS Share** — Based on TTS intensity (GMV / Amazon organic) and page view signal:
   - PV Signal POSITIVE (PVs grew faster than ad spend): higher share (up to 50%)
   - PV Signal NEUTRAL: moderate share (up to 25%)
   - PV Signal NEGATIVE: no attribution
5. **5x GMV Cap** — Attributed lift cannot exceed 5x TTS GMV (prevents over-attribution for large brands)

### Confidence Levels
- **HIGH**: Organic grew + PVs grew + ad spend stable + meaningful TTS
- **MED**: Organic grew + (PVs grew OR ad spend stable)
- **LOW**: Organic grew but other signals mixed
- **WEAK**: TTS active but organic declined
- **INSUF**: Insufficient data

### Estimated Metrics
- **Attributed Organic Lift ($)**: Amazon organic sales attributable to TTS
- **Incremental Page Views**: Amazon PVs above 2024 baseline, at TTS share rate
- **Incremental Units**: Estimated units from attributed lift ÷ revenue per unit
- **Lift per $1 TTS**: Efficiency metric (capped at $5.00)

## Upload 3 Files
1. **Monthly GMV** (.csv) — TTS GMV history by brand
2. **Broadway Tool** (.xlsm) — Content: impressions, visitors, videos
3. **Amazon Report** (.xlsx) — *Required.* 2025 monthly sales by brand

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```
