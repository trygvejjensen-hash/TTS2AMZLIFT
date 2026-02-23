"""
app.py — Amazon Sales Lift from TikTok Activity
Streamlit Dashboard

Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from lift_engine import run_lift_analysis, REQUIRED_COLUMNS

# ── Page Config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="TikTok → Amazon Lift Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom Styling ────────────────────────────────────────────────────────────

st.markdown(
    """
<style>
    .metric-card {
        background: #1a1a2e;
        border-radius: 12px;
        padding: 20px;
        border-left: 4px solid #fe2c55;
    }
    .confidence-High { color: #2ecc71; font-weight: bold; }
    .confidence-Medium { color: #f39c12; font-weight: bold; }
    .confidence-Low { color: #e74c3c; font-weight: bold; }
    .confidence-Inconclusive { color: #95a5a6; font-weight: bold; }
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #fe2c55;
        margin-top: 1rem;
    }
    div[data-testid="stMetric"] {
        background-color: #0e1117;
        border: 1px solid #262730;
        border-radius: 10px;
        padding: 15px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def fmt_currency(val):
    if pd.isna(val):
        return "—"
    if abs(val) >= 1_000_000:
        return f"${val/1_000_000:.2f}M"
    if abs(val) >= 1_000:
        return f"${val/1_000:.1f}K"
    return f"${val:.0f}"


def fmt_pct(val):
    if pd.isna(val):
        return "—"
    return f"{val:+.1f}%"


def fmt_x(val):
    if pd.isna(val) or val == 0:
        return "—"
    return f"{val:.2f}x"


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📈 TTS → Amazon Lift")
    st.markdown("---")

    uploaded_file = st.file_uploader(
        "Upload your summary CSV",
        type=["csv"],
        help=f"Required columns: {', '.join(REQUIRED_COLUMNS)}",
    )

    st.markdown("---")
    st.subheader("⚙️ Settings")

    rolling_window = st.slider(
        "Baseline rolling window (months)",
        min_value=2,
        max_value=12,
        value=3,
        help="Number of prior months used to calculate the expected baseline.",
    )

    st.markdown("---")
    st.markdown(
        """
    **How it works:**
    1. Upload your monthly brand data
    2. We calculate a rolling average baseline
    3. Lift = Actual − Baseline
    4. Confidence flags highlight data quality
    """
    )

# ── Load Data ─────────────────────────────────────────────────────────────────

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        st.stop()
else:
    # Load sample data
    try:
        df = pd.read_csv("sample_data.csv")
        st.info(
            "👆 Using sample data. Upload your own CSV in the sidebar to get started."
        )
    except FileNotFoundError:
        st.warning(
            "No data found. Upload a CSV in the sidebar or place sample_data.csv in this directory."
        )
        st.stop()

# ── Run Analysis ──────────────────────────────────────────────────────────────

results = run_lift_analysis(df, window=rolling_window)

if results["errors"]:
    st.error("⚠️ Data Validation Errors:")
    for err in results["errors"]:
        st.error(f"  • {err}")
    st.stop()

detail = results["detail"]
summary = results["summary"]

# ── Filters ───────────────────────────────────────────────────────────────────

st.title("TikTok → Amazon Sales Lift")

col_filter1, col_filter2 = st.columns([2, 2])

with col_filter1:
    brands = sorted(detail["Brand"].unique())
    selected_brands = st.multiselect(
        "Filter by Brand", brands, default=brands, key="brand_filter"
    )

with col_filter2:
    months = sorted(detail["Month"].unique())
    selected_months = st.multiselect(
        "Filter by Month", months, default=months, key="month_filter"
    )

# Apply filters
detail_f = detail[
    (detail["Brand"].isin(selected_brands)) & (detail["Month"].isin(selected_months))
]
summary_f = summary[summary["Brand"].isin(selected_brands)]

if detail_f.empty:
    st.warning("No data matches the selected filters.")
    st.stop()

# ── KPI Strip ─────────────────────────────────────────────────────────────────

st.markdown("---")

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

total_actual = detail_f["Amazon_Sales"].sum()
total_baseline = detail_f["Baseline_Sales"].sum()
total_lift = detail_f["Lift_Dollars"].sum()
total_spend = detail_f["TikTok_Spend"].sum()
overall_roas = total_lift / total_spend if total_spend > 0 else 0
overall_lift_pct = (total_lift / total_baseline * 100) if total_baseline > 0 else 0

with kpi1:
    st.metric("Total Amazon Sales", fmt_currency(total_actual))
with kpi2:
    st.metric("Baseline Sales", fmt_currency(total_baseline))
with kpi3:
    st.metric(
        "Total Lift $", fmt_currency(total_lift), delta=fmt_pct(overall_lift_pct)
    )
with kpi4:
    st.metric("TikTok Spend", fmt_currency(total_spend))
with kpi5:
    st.metric(
        "Lift ROAS",
        fmt_x(overall_roas),
        help="Every $1 of TikTok spend generated this much in incremental Amazon sales",
    )

st.markdown("---")

# ── Brand Summary Table ───────────────────────────────────────────────────────

st.subheader("🏷️ Brand Summary")

display_summary = summary_f[
    [
        "Brand",
        "Total_Amazon_Sales",
        "Total_Baseline_Sales",
        "Total_Lift_Dollars",
        "Overall_Lift_Pct",
        "Total_TikTok_Spend",
        "Overall_Lift_ROAS",
        "Months_Tracked",
    ]
].copy()

display_summary["Total_Amazon_Sales"] = display_summary["Total_Amazon_Sales"].apply(
    fmt_currency
)
display_summary["Total_Baseline_Sales"] = display_summary[
    "Total_Baseline_Sales"
].apply(fmt_currency)
display_summary["Total_Lift_Dollars"] = display_summary["Total_Lift_Dollars"].apply(
    fmt_currency
)
display_summary["Overall_Lift_Pct"] = display_summary["Overall_Lift_Pct"].apply(
    fmt_pct
)
display_summary["Total_TikTok_Spend"] = display_summary["Total_TikTok_Spend"].apply(
    fmt_currency
)
display_summary["Overall_Lift_ROAS"] = display_summary["Overall_Lift_ROAS"].apply(
    fmt_x
)

display_summary.columns = [
    "Brand",
    "Amazon Sales",
    "Baseline",
    "Lift $",
    "Lift %",
    "TikTok Spend",
    "Lift ROAS",
    "Months",
]

st.dataframe(display_summary, use_container_width=True, hide_index=True)

st.markdown("---")

# ── Charts Row 1: Lift $ Over Time + Lift % by Brand ─────────────────────────

col_l, col_r = st.columns([3, 2])

with col_l:
    st.subheader("📅 Monthly Lift $ Over Time")
    monthly_agg = (
        detail_f.groupby("Month")
        .agg({"Lift_Dollars": "sum", "TikTok_Spend": "sum"})
        .reset_index()
    )
    fig_monthly = go.Figure()
    fig_monthly.add_trace(
        go.Bar(
            x=monthly_agg["Month"],
            y=monthly_agg["Lift_Dollars"],
            name="Lift $",
            marker_color="#fe2c55",
        )
    )
    fig_monthly.add_trace(
        go.Scatter(
            x=monthly_agg["Month"],
            y=monthly_agg["TikTok_Spend"],
            name="TikTok Spend",
            yaxis="y2",
            line=dict(color="#25f4ee", width=2),
        )
    )
    fig_monthly.update_layout(
        yaxis=dict(title="Lift $", side="left"),
        yaxis2=dict(title="TikTok Spend", side="right", overlaying="y"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=400,
        margin=dict(l=50, r=50, t=30, b=50),
    )
    st.plotly_chart(fig_monthly, use_container_width=True)

with col_r:
    st.subheader("📊 Lift ROAS by Brand")
    brand_roas = summary_f[["Brand", "Overall_Lift_ROAS"]].sort_values(
        "Overall_Lift_ROAS", ascending=True
    )
    fig_roas = px.bar(
        brand_roas,
        x="Overall_Lift_ROAS",
        y="Brand",
        orientation="h",
        color="Overall_Lift_ROAS",
        color_continuous_scale=["#fe2c55", "#25f4ee"],
    )
    fig_roas.update_layout(
        showlegend=False,
        height=400,
        margin=dict(l=50, r=30, t=30, b=50),
        xaxis_title="Lift ROAS",
        yaxis_title="",
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_roas, use_container_width=True)

st.markdown("---")

# ── Charts Row 2: Actual vs Baseline + Spend vs Lift Scatter ─────────────────

col_l2, col_r2 = st.columns(2)

with col_l2:
    st.subheader("📈 Actual vs. Baseline (All Brands)")
    monthly_totals = (
        detail_f.groupby("Month")
        .agg({"Amazon_Sales": "sum", "Baseline_Sales": "sum"})
        .reset_index()
    )
    fig_avb = go.Figure()
    fig_avb.add_trace(
        go.Scatter(
            x=monthly_totals["Month"],
            y=monthly_totals["Amazon_Sales"],
            name="Actual Sales",
            line=dict(color="#fe2c55", width=3),
            fill="tonexty",
        )
    )
    fig_avb.add_trace(
        go.Scatter(
            x=monthly_totals["Month"],
            y=monthly_totals["Baseline_Sales"],
            name="Baseline",
            line=dict(color="#ffffff", width=2, dash="dash"),
        )
    )
    fig_avb.update_layout(
        height=400,
        margin=dict(l=50, r=30, t=30, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_avb, use_container_width=True)

with col_r2:
    st.subheader("💰 TikTok Spend vs. Lift $")
    fig_scatter = px.scatter(
        detail_f,
        x="TikTok_Spend",
        y="Lift_Dollars",
        color="Brand",
        size="TikTok_Views",
        hover_data=["Month", "Confidence"],
        size_max=30,
    )
    fig_scatter.update_layout(
        height=400,
        margin=dict(l=50, r=30, t=30, b=50),
        xaxis_title="TikTok Spend ($)",
        yaxis_title="Lift ($)",
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

st.markdown("---")

# ── Detail Table ──────────────────────────────────────────────────────────────

st.subheader("📋 Monthly Detail")

detail_display = detail_f[
    [
        "Brand",
        "Month",
        "Amazon_Sales",
        "Baseline_Sales",
        "Lift_Dollars",
        "Lift_Pct",
        "TikTok_Spend",
        "Lift_ROAS",
        "Confidence",
    ]
].copy()

detail_display.columns = [
    "Brand",
    "Month",
    "Amazon Sales",
    "Baseline",
    "Lift $",
    "Lift %",
    "TikTok Spend",
    "Lift ROAS",
    "Confidence",
]

st.dataframe(detail_display, use_container_width=True, hide_index=True)

# ── Downloads ─────────────────────────────────────────────────────────────────

st.markdown("---")

col_dl1, col_dl2 = st.columns(2)

with col_dl1:
    csv_detail = detail_f.to_csv(index=False)
    st.download_button(
        label="⬇️ Download Monthly Detail CSV",
        data=csv_detail,
        file_name="lift_detail.csv",
        mime="text/csv",
    )

with col_dl2:
    csv_summary = summary_f.to_csv(index=False)
    st.download_button(
        label="⬇️ Download Brand Summary CSV",
        data=csv_summary,
        file_name="lift_summary.csv",
        mime="text/csv",
    )
