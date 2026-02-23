"""
lift_engine.py — Amazon Sales Lift from TikTok Activity
Core Calculation Engine

All math lives here, completely separate from the UI. You can import it
in other scripts, run it in notebooks, or swap out the baseline logic
later without touching the dashboard.
"""

import pandas as pd
import numpy as np

# ── Required Columns ──────────────────────────────────────────────────────────

REQUIRED_COLUMNS = [
    "Brand",
    "Month",
    "Amazon_Sales",
    "TikTok_Spend",
    "TikTok_Impressions",
    "TikTok_Views",
    "TikTok_Engagements",
    "TikTok_Clicks",
]

OPTIONAL_COLUMNS = ["External_Event"]


# ── Validation ────────────────────────────────────────────────────────────────

def validate_data(df: pd.DataFrame) -> tuple[bool, list[str]]:
    """
    Validates the input dataframe has required columns and reasonable values.
    Returns (is_valid, list_of_errors).
    """
    errors = []

    # Check required columns
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        errors.append(f"Missing required columns: {', '.join(missing)}")
        return False, errors

    # Check for empty data
    if len(df) == 0:
        errors.append("Dataset is empty.")
        return False, errors

    # Check numeric columns
    numeric_cols = [c for c in REQUIRED_COLUMNS if c not in ("Brand", "Month")]
    for col in numeric_cols:
        if not pd.api.types.is_numeric_dtype(df[col]):
            errors.append(f"Column '{col}' must be numeric.")

    # Check for negative sales
    if (df["Amazon_Sales"] < 0).any():
        errors.append("Amazon_Sales contains negative values.")

    # Check month format
    try:
        pd.to_datetime(df["Month"], format="%Y-%m")
    except (ValueError, TypeError):
        errors.append("Month column must be in YYYY-MM format (e.g., 2024-01).")

    return len(errors) == 0, errors


# ── Data Preparation ──────────────────────────────────────────────────────────

def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and sort data for analysis."""
    df = df.copy()
    df["Month_Date"] = pd.to_datetime(df["Month"], format="%Y-%m")
    df = df.sort_values(["Brand", "Month_Date"]).reset_index(drop=True)

    # Fill optional columns
    if "External_Event" not in df.columns:
        df["External_Event"] = ""
    df["External_Event"] = df["External_Event"].fillna("").astype(str)

    return df


# ── Baseline Calculation ──────────────────────────────────────────────────────

def compute_rolling_baseline(df: pd.DataFrame, window: int = 3) -> pd.DataFrame:
    """
    Compute rolling average baseline per brand.
    Uses the previous N months of Amazon sales as the expected baseline.
    """
    df = df.copy()

    df["Baseline_Sales"] = (
        df.groupby("Brand")["Amazon_Sales"]
        .transform(lambda x: x.shift(1).rolling(window=window, min_periods=1).mean())
    )

    # For the very first month(s) where we have no history, use the actual
    # sales as baseline (lift = 0, which is honest — we can't measure yet)
    df["Baseline_Sales"] = df["Baseline_Sales"].fillna(df["Amazon_Sales"])

    return df


# ── Lift Metrics ──────────────────────────────────────────────────────────────

def compute_lift_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate lift dollars, percentage, ROAS, and cost per lift dollar."""
    df = df.copy()

    # Core lift
    df["Lift_Dollars"] = df["Amazon_Sales"] - df["Baseline_Sales"]
    df["Lift_Pct"] = np.where(
        df["Baseline_Sales"] > 0,
        (df["Lift_Dollars"] / df["Baseline_Sales"]) * 100,
        0,
    )

    # Efficiency metrics
    df["Lift_ROAS"] = np.where(
        df["TikTok_Spend"] > 0,
        df["Lift_Dollars"] / df["TikTok_Spend"],
        0,
    )
    df["Cost_Per_Lift_Dollar"] = np.where(
        df["Lift_Dollars"] > 0,
        df["TikTok_Spend"] / df["Lift_Dollars"],
        np.nan,
    )

    # Engagement efficiency
    df["Lift_Per_1K_Views"] = np.where(
        df["TikTok_Views"] > 0,
        df["Lift_Dollars"] / (df["TikTok_Views"] / 1000),
        0,
    )
    df["Lift_Per_1K_Impressions"] = np.where(
        df["TikTok_Impressions"] > 0,
        df["Lift_Dollars"] / (df["TikTok_Impressions"] / 1000),
        0,
    )

    return df


# ── Confidence Flags ──────────────────────────────────────────────────────────

def apply_confidence_flags(df: pd.DataFrame, window: int = 3) -> pd.DataFrame:
    """
    Apply confidence flags based on data quality and external events.

    High:          Enough baseline history, no external events, positive lift
    Medium:        Enough history but external event present OR negative lift
    Low:           External event AND negative lift
    Inconclusive:  Not enough baseline history or zero TikTok spend
    """
    df = df.copy()

    # Count months of history per brand up to each row
    df["Months_Of_History"] = df.groupby("Brand").cumcount()

    conditions = []
    choices = []

    # Inconclusive: not enough data or no spend
    conditions.append(
        (df["Months_Of_History"] < window) | (df["TikTok_Spend"] == 0)
    )
    choices.append("Inconclusive")

    # Low: external event + negative lift
    conditions.append(
        (df["External_Event"].str.len() > 0) & (df["Lift_Dollars"] < 0)
    )
    choices.append("Low")

    # Medium: external event OR negative lift
    conditions.append(
        (df["External_Event"].str.len() > 0) | (df["Lift_Dollars"] < 0)
    )
    choices.append("Medium")

    # High: everything else (enough data, no events, positive lift)
    conditions.append(pd.Series(True, index=df.index))
    choices.append("High")

    df["Confidence"] = np.select(conditions, choices, default="Medium")

    return df


# ── Brand Summary ─────────────────────────────────────────────────────────────

def compute_brand_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate lift metrics at the brand level."""
    summary = (
        df.groupby("Brand")
        .agg(
            Total_Amazon_Sales=("Amazon_Sales", "sum"),
            Total_Baseline_Sales=("Baseline_Sales", "sum"),
            Total_Lift_Dollars=("Lift_Dollars", "sum"),
            Total_TikTok_Spend=("TikTok_Spend", "sum"),
            Total_Views=("TikTok_Views", "sum"),
            Total_Impressions=("TikTok_Impressions", "sum"),
            Months_Tracked=("Month", "count"),
            Avg_Monthly_Lift=("Lift_Dollars", "mean"),
            Avg_Lift_Pct=("Lift_Pct", "mean"),
        )
        .reset_index()
    )

    # Overall ROAS
    summary["Overall_Lift_ROAS"] = np.where(
        summary["Total_TikTok_Spend"] > 0,
        summary["Total_Lift_Dollars"] / summary["Total_TikTok_Spend"],
        0,
    )

    # Overall Lift %
    summary["Overall_Lift_Pct"] = np.where(
        summary["Total_Baseline_Sales"] > 0,
        (summary["Total_Lift_Dollars"] / summary["Total_Baseline_Sales"]) * 100,
        0,
    )

    return summary.sort_values("Total_Lift_Dollars", ascending=False)


# ── Main Pipeline ─────────────────────────────────────────────────────────────

def run_lift_analysis(
    df: pd.DataFrame,
    window: int = 3,
) -> dict:
    """
    Full pipeline: validate → prepare → baseline → lift → confidence → summarize.

    Returns a dict with:
      - 'detail': row-level dataframe
      - 'summary': brand-level summary
      - 'errors': list of validation errors (empty if clean)
      - 'window': rolling window used
    """
    is_valid, errors = validate_data(df)
    if not is_valid:
        return {"detail": None, "summary": None, "errors": errors, "window": window}

    df = prepare_data(df)
    df = compute_rolling_baseline(df, window=window)
    df = compute_lift_metrics(df)
    df = apply_confidence_flags(df, window=window)
    summary = compute_brand_summary(df)

    return {
        "detail": df,
        "summary": summary,
        "errors": [],
        "window": window,
    }
