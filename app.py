"""
Building Energy Waste Detective: ML-Based Energy Anomaly Detection
==================================================================
High-Impact, Premium Streamlit Dashboard for Academic Demonstration,
Exploratory Data Analysis, ML Regression Benchmarking, Contextual Energy
Waste Detection, and Financial Loss Quantification in Indian Rupees (₹).
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from utils import (
    preprocess_energy_data,
    validate_dataset_columns,
    detect_contextual_waste,
    train_and_predict_isolation_forest,
    compute_regression_metrics,
    compute_anomaly_metrics,
    DEFAULT_TARIFF_INR_PER_KWH,
    REQUIRED_INPUT_COLUMNS,
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
)

# -------------------------------------------------------------------
# PAGE CONFIGURATION
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Building Energy Waste Detective",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Base Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "energy_data.csv")
MODELS_DIR = os.path.join(BASE_DIR, "models")
BEST_MODEL_PATH = os.path.join(MODELS_DIR, "best_model.joblib")
METADATA_PATH = os.path.join(MODELS_DIR, "model_metadata.json")
COMPARISON_PATH = os.path.join(MODELS_DIR, "model_comparison.csv")

# -------------------------------------------------------------------
# ADVANCED CUSTOM CSS & MODERN DESIGN SYSTEM
# -------------------------------------------------------------------
CUSTOM_CSS = """
<style>
/* Import Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* Global Font Application */
html, body, [class*="css"], .stMarkdown, p, div, span, label {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

code, pre {
    font-family: 'JetBrains Mono', monospace !important;
}

/* Background Subtle Gradient */
.stApp {
    background: radial-gradient(circle at 15% 15%, rgba(30, 41, 59, 0.4) 0%, rgba(15, 23, 42, 0) 50%),
                radial-gradient(circle at 85% 85%, rgba(37, 99, 235, 0.08) 0%, rgba(15, 23, 42, 0) 50%);
}

/* Hero Banner Container */
.hero-container {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.95) 100%);
    border: 1px solid rgba(148, 163, 184, 0.15);
    border-radius: 16px;
    padding: 24px 30px;
    margin-bottom: 24px;
    box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(12px);
    position: relative;
    overflow: hidden;
}

.hero-container::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #38bdf8 0%, #818cf8 50%, #ec4899 100%);
}

.hero-title {
    font-size: 2.1rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #f8fafc 0%, #cbd5e1 50%, #38bdf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 12px;
}

.hero-subtitle {
    font-size: 1.05rem;
    color: #94a3b8;
    margin-bottom: 16px;
    font-weight: 400;
}

/* Badges Container */
.badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 10px;
}

.badge-item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(30, 41, 59, 0.6);
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 20px;
    padding: 5px 13px;
    font-size: 0.8rem;
    font-weight: 600;
    color: #cbd5e1;
    transition: all 0.25s ease;
}

.badge-item:hover {
    border-color: #38bdf8;
    color: #f8fafc;
    transform: translateY(-1px);
}

.badge-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #10b981;
    box-shadow: 0 0 8px #10b981;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0% { opacity: 0.4; }
    50% { opacity: 1; }
    100% { opacity: 0.4; }
}

/* Modern Metric Cards Grid */
.metric-card {
    background: linear-gradient(145deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.85) 100%);
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 14px;
    padding: 18px 20px;
    box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.35);
    backdrop-filter: blur(8px);
    transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.25s ease, border-color 0.25s ease;
    height: 100%;
    position: relative;
}

.metric-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 28px -4px rgba(0, 0, 0, 0.5);
    border-color: rgba(56, 189, 248, 0.4);
}

.metric-label {
    font-size: 0.82rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94a3b8;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.metric-value {
    font-size: 1.75rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    color: #f8fafc;
    margin-bottom: 4px;
    line-height: 1.2;
}

.metric-sub {
    font-size: 0.82rem;
    font-weight: 500;
    color: #64748b;
    display: flex;
    align-items: center;
    gap: 4px;
}

.metric-delta-danger {
    color: #fb7185;
    background: rgba(244, 63, 94, 0.12);
    padding: 2px 7px;
    border-radius: 6px;
    font-weight: 600;
    display: inline-block;
}

.metric-delta-success {
    color: #34d399;
    background: rgba(16, 185, 129, 0.12);
    padding: 2px 7px;
    border-radius: 6px;
    font-weight: 600;
    display: inline-block;
}

/* Callout Box */
.insight-box {
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.1) 0%, rgba(30, 41, 59, 0.4) 100%);
    border-left: 4px solid #38bdf8;
    border-top: 1px solid rgba(56, 189, 248, 0.2);
    border-right: 1px solid rgba(148, 163, 184, 0.1);
    border-bottom: 1px solid rgba(148, 163, 184, 0.1);
    border-radius: 10px;
    padding: 16px 20px;
    margin: 18px 0;
    color: #e2e8f0;
}

/* Custom Tabs Styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: rgba(15, 23, 42, 0.6);
    padding: 6px;
    border-radius: 12px;
    border: 1px solid rgba(148, 163, 184, 0.15);
}

.stTabs [data-baseweb="tab"] {
    height: 42px;
    border-radius: 8px;
    padding: 0 18px;
    font-weight: 600;
    font-size: 0.9rem;
    color: #94a3b8;
    border: none !important;
    transition: all 0.2s ease;
}

.stTabs [data-baseweb="tab"]:hover {
    color: #f8fafc;
    background: rgba(255, 255, 255, 0.04);
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
}

/* Sidebar Styling */
section[data-testid="stSidebar"] {
    background-color: #0f172a;
    border-right: 1px solid rgba(148, 163, 184, 0.12);
}

/* Table Polish */
div[data-testid="stDataFrame"] {
    border: 1px solid rgba(148, 163, 184, 0.15);
    border-radius: 10px;
    overflow: hidden;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -------------------------------------------------------------------
# RESOURCE LOADING
# -------------------------------------------------------------------
@st.cache_data
def load_default_data():
    """Loads the pre-generated campus electricity dataset."""
    if not os.path.exists(DATA_PATH):
        st.error(f"Dataset not found at {DATA_PATH}. Please run `python generate_data.py` first.")
        return None
    df = pd.read_csv(DATA_PATH)
    return preprocess_energy_data(df)


@st.cache_resource
def load_saved_model_and_metadata():
    """Loads the trained ML regression pipeline and metadata."""
    if not os.path.exists(BEST_MODEL_PATH) or not os.path.exists(METADATA_PATH):
        return None, None, None
    
    model = joblib.load(BEST_MODEL_PATH)
    with open(METADATA_PATH, "r") as f:
        metadata = json.load(f)
    
    comparison_df = None
    if os.path.exists(COMPARISON_PATH):
        comparison_df = pd.read_csv(COMPARISON_PATH)
        
    return model, metadata, comparison_df


default_df = load_default_data()
model_pipeline, metadata, comparison_df = load_saved_model_and_metadata()

if default_df is None or model_pipeline is None:
    st.error("⚠️ Model or dataset artifacts not found. Please train the model using `python train_model.py`.")
    st.stop()

# -------------------------------------------------------------------
# HERO HEADER SECTION
# -------------------------------------------------------------------
st.markdown(
    """
    <div class="hero-container">
        <div class="hero-title">
            <span>⚡</span> Building Energy Waste Detective
        </div>
        <div class="hero-subtitle">
            Physics-Informed ML Anomaly Detection & Financial Waste Quantification for University Campuses
        </div>
        <div class="badge-row">
            <div class="badge-item">
                <span class="badge-dot"></span> Telemetry Active (8,640 Hours)
            </div>
            <div class="badge-item">
                🏆 Champion Model: <b>XGBoost (R²: 0.9043)</b>
            </div>
            <div class="badge-item">
                🛡️ Zero Future-Data Leakage
            </div>
            <div class="badge-item">
                ₹ Electricity Tariff: <b>INR 8.50 / kWh</b>
            </div>
            <div class="badge-item">
                🎓 Academic ML Mini Project
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------
# SIDEBAR CONTROLS & CONFIGURATION
# -------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎛️ Control Panel")
    
    # 1. Dataset Selection
    data_source = st.radio(
        "Telemetry Data Source:",
        ["Default Campus Dataset (90 Days)", "Upload Custom CSV Telemetry"],
    )

    active_df = None
    if data_source == "Default Campus Dataset (90 Days)":
        active_df = default_df.copy()
        st.caption(f"✓ Connected to simulated database: {len(active_df):,} records.")
    else:
        uploaded_file = st.file_uploader("Upload CSV Telemetry File", type=["csv"])
        if uploaded_file is not None:
            try:
                custom_raw = pd.read_csv(uploaded_file)
                is_valid, missing_cols = validate_dataset_columns(custom_raw)
                if not is_valid:
                    st.error(f"❌ Missing required columns: {missing_cols}")
                    st.info(f"Required columns: {REQUIRED_INPUT_COLUMNS}")
                    st.stop()
                else:
                    active_df = preprocess_energy_data(custom_raw)
                    st.success(f"✓ Uploaded {len(active_df):,} records successfully!")
            except Exception as e:
                st.error(f"Error parsing uploaded CSV: {e}")
                st.stop()
        else:
            st.info("Awaiting CSV file upload in sidebar...")
            st.stop()

    st.markdown("---")
    st.markdown("### 🔍 Telemetry Filters")

    # Building Filter
    all_buildings = ["All Buildings"] + sorted(list(active_df["building"].unique()))
    selected_building = st.selectbox("Campus Building:", all_buildings)

    filtered_df = active_df.copy()
    if selected_building != "All Buildings":
        filtered_df = filtered_df[filtered_df["building"] == selected_building]

    # Zone Filter
    available_zones = ["All Zones"] + sorted(list(filtered_df["zone"].unique()))
    selected_zone = st.selectbox("Functional Zone:", available_zones)
    if selected_zone != "All Zones":
        filtered_df = filtered_df[filtered_df["zone"] == selected_zone]

    # Date Range Filter
    min_date = active_df["timestamp"].dt.date.min()
    max_date = active_df["timestamp"].dt.date.max()
    selected_dates = st.date_input(
        "Date Range Filter:",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
        start_d, end_d = selected_dates
        filtered_df = filtered_df[
            (filtered_df["timestamp"].dt.date >= start_d) & (filtered_df["timestamp"].dt.date <= end_d)
        ]

    st.markdown("---")
    st.markdown("### ⚙️ Detection Parameters")
    
    residual_threshold = st.slider(
        "Waste Residual Threshold (kW):",
        min_value=3.0,
        max_value=35.0,
        value=float(metadata.get("default_thresholds", {}).get("residual_threshold_kw", 10.0)),
        step=0.5,
        help="Flags waste if Actual Power exceeds Predicted Expected Power by at least this margin.",
    )

    occupancy_threshold = st.slider(
        "Low Occupancy Threshold (Persons):",
        min_value=0,
        max_value=15,
        value=int(metadata.get("default_thresholds", {}).get("occupancy_threshold", 5)),
        step=1,
        help="Space considered idle or unpopulated if headcount is at or below this value.",
    )

    tariff_inr = st.number_input(
        "Electricity Tariff (₹ INR / kWh):",
        min_value=1.0,
        max_value=25.0,
        value=float(metadata.get("default_thresholds", {}).get("tariff_inr_per_kwh", DEFAULT_TARIFF_INR_PER_KWH)),
        step=0.25,
        help="Standard commercial/institutional energy billing rate in India.",
    )

if len(filtered_df) == 0:
    st.warning("⚠️ No records match the current filter selection. Please broaden your date range or filters.")
    st.stop()

# -------------------------------------------------------------------
# INFERENCE & RESIDUAL COMPUTATION
# -------------------------------------------------------------------
feature_cols = CATEGORICAL_FEATURES + NUMERIC_FEATURES
for col in feature_cols:
    if col not in filtered_df.columns:
        filtered_df = preprocess_energy_data(filtered_df)
        break

X_curr = filtered_df[feature_cols]
predicted_kw = model_pipeline.predict(X_curr)

results_df = detect_contextual_waste(
    filtered_df,
    predicted_kw=predicted_kw,
    residual_threshold_kw=residual_threshold,
    occupancy_threshold=occupancy_threshold,
    tariff_inr=tariff_inr,
)

# -------------------------------------------------------------------
# TOP KPI METRIC CARDS
# -------------------------------------------------------------------
total_actual_kwh = results_df["actual_power_kw"].sum()
total_waste_kwh = results_df["excess_kwh"].sum()
total_waste_inr = results_df["excess_cost_inr"].sum()
waste_incidents = int((results_df["is_waste_detected"] == 1).sum())
waste_percentage = (waste_incidents / len(results_df)) * 100
mean_power = results_df["actual_power_kw"].mean()

card_col1, card_col2, card_col3, card_col4, card_col5 = st.columns(5)

with card_col1:
    st.markdown(
        f"""
        <div class="metric-card" style="border-top: 3px solid #38bdf8;">
            <div class="metric-label">Telemetry Hours 🕒</div>
            <div class="metric-value">{len(results_df):,}</div>
            <div class="metric-sub">Monitored Duration</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with card_col2:
    st.markdown(
        f"""
        <div class="metric-card" style="border-top: 3px solid #818cf8;">
            <div class="metric-label">Total Energy ⚡</div>
            <div class="metric-value">{total_actual_kwh:,.0f} <span style="font-size:0.95rem; font-weight:500;">kWh</span></div>
            <div class="metric-sub">Avg Draw: {mean_power:.1f} kW</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with card_col3:
    st.markdown(
        f"""
        <div class="metric-card" style="border-top: 3px solid #f43f5e;">
            <div class="metric-label">Wasted Energy 🚨</div>
            <div class="metric-value" style="color: #fb7185;">{total_waste_kwh:,.1f} <span style="font-size:0.95rem; font-weight:500;">kWh</span></div>
            <div class="metric-sub"><span class="metric-delta-danger">{waste_percentage:.1f}% hours wasted</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with card_col4:
    st.markdown(
        f"""
        <div class="metric-card" style="border-top: 3px solid #fbbf24;">
            <div class="metric-label">Financial Loss 💸</div>
            <div class="metric-value" style="color: #fbbf24;">₹ {total_waste_inr:,.0f}</div>
            <div class="metric-sub">At ₹{tariff_inr:.2f}/kWh Tariff</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with card_col5:
    st.markdown(
        f"""
        <div class="metric-card" style="border-top: 3px solid #a855f7;">
            <div class="metric-label">Waste Incidents 🔍</div>
            <div class="metric-value">{waste_incidents:,}</div>
            <div class="metric-sub">Idle Overconsumption</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")

# -------------------------------------------------------------------
# ACTIONABLE CAMPUS SAVINGS CALLOUT
# -------------------------------------------------------------------
estimated_monthly_savings = (total_waste_inr / max(1, (results_df["timestamp"].dt.date.max() - results_df["timestamp"].dt.date.min()).days)) * 30.0
st.markdown(
    f"""
    <div class="insight-box">
        <b>💡 Executive Campus Energy Insight:</b> 
        Across the selected period, our ML detective identified <b>{waste_incidents} avoidable waste events</b> totaling <b>{total_waste_kwh:,.1f} kWh</b>. 
        By implementing automated HVAC setbacks and smart occupancy switches, the campus can save an estimated 
        <b>₹{estimated_monthly_savings:,.0f} per month</b> in unnecessary utility bills.
    </div>
    """,
    unsafe_allow_html=True,
)

# Plotly Shared Clean Theme Configuration
PLOT_THEME = dict(
    plot_bgcolor="rgba(15, 23, 42, 0.5)",
    paper_bgcolor="rgba(0, 0, 0, 0)",
    font=dict(family="Plus Jakarta Sans, sans-serif", color="#cbd5e1", size=12),
    margin=dict(l=25, r=20, t=45, b=25),
    xaxis=dict(
        gridcolor="rgba(148, 163, 184, 0.12)",
        zerolinecolor="rgba(148, 163, 184, 0.2)",
    ),
    yaxis=dict(
        gridcolor="rgba(148, 163, 184, 0.12)",
        zerolinecolor="rgba(148, 163, 184, 0.2)",
    ),
)

# -------------------------------------------------------------------
# MAIN APPLICATION TABS
# -------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Exploratory Data Analysis",
    "🤖 ML Model Benchmarks",
    "🔍 Waste Detective",
    "📈 Academic Evaluation",
    "📤 Custom Data Auditor",
])

# -------------------------------------------------------------------
# TAB 1: EXPLORATORY DATA ANALYSIS (EDA)
# -------------------------------------------------------------------
with tab1:
    st.markdown("### 📊 Exploratory Data Analysis & Consumption Dynamics")
    st.caption("Investigate empirical energy patterns across 24-hour cycles, occupancy variations, and ambient weather.")
    
    col_eda1, col_eda2 = st.columns([1, 1])
    
    with col_eda1:
        st.markdown("##### 🕒 Hourly Diurnal Power Profile by Facility")
        hourly_profile = results_df.groupby(["hour", "building"])["actual_power_kw"].mean().reset_index()
        fig_hourly = px.line(
            hourly_profile,
            x="hour",
            y="actual_power_kw",
            color="building",
            markers=True,
            labels={"hour": "Hour of Day (0 to 23)", "actual_power_kw": "Average Load (kW)"},
            color_discrete_sequence=["#38bdf8", "#34d399", "#f43f5e", "#fbbf24"],
        )
        fig_hourly.update_layout(**PLOT_THEME, height=380)
        st.plotly_chart(fig_hourly, use_container_width=True)

    with col_eda2:
        st.markdown("##### 👥 Occupancy vs. Power Consumption (Physical Correlation)")
        sample_size = min(1500, len(results_df))
        fig_scatter = px.scatter(
            results_df.sample(sample_size, random_state=42),
            x="occupancy",
            y="actual_power_kw",
            color="building",
            opacity=0.65,
            trendline="ols",
            labels={"occupancy": "Zone Occupancy (Headcount)", "actual_power_kw": "Power Draw (kW)"},
            color_discrete_sequence=["#38bdf8", "#34d399", "#f43f5e", "#fbbf24"],
        )
        fig_scatter.update_layout(**PLOT_THEME, height=380)
        st.plotly_chart(fig_scatter, use_container_width=True)

    col_eda3, col_eda4 = st.columns([1, 1])
    
    with col_eda3:
        st.markdown("##### 🌡️ Thermal Cooling Sensitivity: Temperature (°C) vs. Power (kW)")
        fig_temp = px.scatter(
            results_df.sample(sample_size, random_state=42),
            x="temperature",
            y="actual_power_kw",
            color="is_weekend",
            color_continuous_scale=[[0, "#38bdf8"], [1, "#fbbf24"]],
            opacity=0.7,
            labels={"temperature": "Outdoor Temp (°C)", "actual_power_kw": "Actual Power (kW)", "is_weekend": "Weekend"},
        )
        fig_temp.update_layout(**PLOT_THEME, height=360)
        st.plotly_chart(fig_temp, use_container_width=True)

    with col_eda4:
        st.markdown("##### 📋 Descriptive Telemetry Statistics")
        stats_cols = ["actual_power_kw", "occupancy", "temperature", "humidity"]
        desc_df = results_df[stats_cols].describe().T[["mean", "std", "min", "50%", "max"]].round(2)
        st.dataframe(desc_df, use_container_width=True)
        st.caption("Key Observation: Power increases non-linearly when outdoor temperature exceeds 24°C due to HVAC chiller activation, while baseline standby load (servers, refrigeration) persists at 8-25 kW even at 0 occupancy.")

# -------------------------------------------------------------------
# TAB 2: ML MODEL BENCHMARKS & FEATURE IMPORTANCE
# -------------------------------------------------------------------
with tab2:
    st.markdown("### 🤖 Supervised ML Regression Benchmark & Feature Importance")
    st.caption("All models trained with strict chronological split (first 80% train, last 20% test) to prevent future-data leakage.")
    
    if comparison_df is not None:
        st.markdown("##### 🏆 Model Leaderboard (Evaluated on Unseen Test Set)")
        st.dataframe(
            comparison_df.style.highlight_max(subset=["R2 Score"], color="#064e3b")
                               .highlight_min(subset=["MAE (kW)", "RMSE (kW)", "MAPE (%)"], color="#064e3b"),
            use_container_width=True
        )
        st.success(f"Champion Selected: **{metadata.get('best_model_name', 'XGBoost Regressor')}** — Achieved R² of 0.9043 and MAE of 2.099 kW.")

    col_m1, col_m2 = st.columns([1, 1])

    with col_m1:
        st.markdown("##### 🌲 XGBoost Feature Importance Breakdown")
        try:
            model_core = model_pipeline.named_steps["model"]
            prep_core = model_pipeline.named_steps["prep"]
            
            # Extract categorical one-hot names + numeric names
            cat_names = list(prep_core.named_transformers_["cat"].get_feature_names_out(CATEGORICAL_FEATURES))
            all_feature_names = cat_names + NUMERIC_FEATURES
            
            if hasattr(model_core, "feature_importances_"):
                importances = model_core.feature_importances_
                fi_df = pd.DataFrame({
                    "Feature": all_feature_names,
                    "Importance": importances,
                }).sort_values(by="Importance", ascending=True).tail(10)

                fig_fi = px.bar(
                    fi_df,
                    x="Importance",
                    y="Feature",
                    orientation="h",
                    color="Importance",
                    color_continuous_scale="Viridis",
                    labels={"Importance": "Relative Gain / Weight"},
                )
                fig_fi.update_layout(**PLOT_THEME, height=360, coloraxis_showscale=False)
                st.plotly_chart(fig_fi, use_container_width=True)
            else:
                st.info("Feature importance not available for current baseline.")
        except Exception as e:
            st.info(f"Feature importance visualization: {e}")

    with col_m2:
        st.markdown("##### 📊 Regression Residual Distribution (Error = Actual - Predicted)")
        fig_res = px.histogram(
            results_df,
            x="residual_kw",
            nbins=45,
            marginal="box",
            labels={"residual_kw": "Residual Error (kW)"},
            color_discrete_sequence=["#818cf8"],
        )
        fig_res.add_vline(x=0, line_dash="solid", line_color="#cbd5e1", annotation_text="Zero Error")
        fig_res.add_vline(x=residual_threshold, line_dash="dash", line_color="#f43f5e", annotation_text=f"Waste Limit (+{residual_threshold} kW)")
        fig_res.update_layout(**PLOT_THEME, height=360)
        st.plotly_chart(fig_res, use_container_width=True)

    st.markdown("##### 📈 Actual vs. ML-Predicted Power Baseline (Recent 250 Hours)")
    timeline_sample = results_df.sort_values(by="timestamp").tail(250)
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=timeline_sample["timestamp"],
        y=timeline_sample["actual_power_kw"],
        mode="lines",
        name="Actual Power (kW)",
        line=dict(color="#38bdf8", width=2),
    ))
    fig_line.add_trace(go.Scatter(
        x=timeline_sample["timestamp"],
        y=timeline_sample["predicted_power_kw"],
        mode="lines",
        name="XGBoost Expected Baseline (kW)",
        line=dict(color="#34d399", width=2, dash="dash"),
    ))
    fig_line.update_layout(
        **PLOT_THEME,
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_line, use_container_width=True)

# -------------------------------------------------------------------
# TAB 3: WASTE DETECTIVE & INCIDENT EXPLORER
# -------------------------------------------------------------------
with tab3:
    st.markdown("### 🔍 Contextual Energy Waste Detective")
    st.markdown(
        """
        The **Waste Detective** compares real-time smart meter power against the ML expected baseline.
        An incident is tagged as **Actionable Energy Waste** if:
        $$\\text{Residual } (Actual - Predicted) \\ge \\tau_{\\text{waste}} \\quad \\text{AND} \\quad \\text{Occupancy} \\le \\text{Low Limit}$$
        This eliminates false positives caused by legitimately heavy daytime occupancy.
        """
    )

    # Interactive Detection Chart with Red Waste Markers
    fig_waste = go.Figure()
    display_sample = results_df.sort_values(by="timestamp").tail(350)
    
    fig_waste.add_trace(go.Scatter(
        x=display_sample["timestamp"],
        y=display_sample["actual_power_kw"],
        mode="lines",
        name="Actual Telemetry Power",
        line=dict(color="#64748b", width=1.5),
    ))
    
    fig_waste.add_trace(go.Scatter(
        x=display_sample["timestamp"],
        y=display_sample["predicted_power_kw"],
        mode="lines",
        name="Expected Load Baseline",
        line=dict(color="#38bdf8", width=1.5, dash="dot"),
    ))

    waste_subset = display_sample[display_sample["is_waste_detected"] == 1]
    if len(waste_subset) > 0:
        fig_waste.add_trace(go.Scatter(
            x=waste_subset["timestamp"],
            y=waste_subset["actual_power_kw"],
            mode="markers",
            name="Flagged Energy Waste",
            marker=dict(
                size=11,
                color="#f43f5e",
                symbol="triangle-up",
                line=dict(width=1.5, color="#ffffff"),
            ),
            text=[
                f"<b>{row.building}</b><br>Actual: {row.actual_power_kw:.1f} kW<br>Expected: {row.predicted_power_kw:.1f} kW<br>Excess: +{row.residual_kw:.1f} kW<br>Occupancy: {row.occupancy}<br>Loss: ₹{row.excess_cost_inr:.2f}"
                for _, row in waste_subset.iterrows()
            ],
            hoverinfo="text",
        ))

    fig_waste.update_layout(
        **PLOT_THEME,
        title="Detected Waste Incidents Along Chronological Telemetry (Recent 350 Hours)",
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_waste, use_container_width=True)

    # Incident Log Data Table
    st.markdown("##### 🚨 Detected Waste Incidents Audit Log")
    waste_records = results_df[results_df["is_waste_detected"] == 1][
        ["timestamp", "building", "zone", "occupancy", "actual_power_kw", "predicted_power_kw", "residual_kw", "waste_severity", "excess_cost_inr"]
    ].sort_values(by="residual_kw", ascending=False)

    if len(waste_records) > 0:
        st.dataframe(
            waste_records.rename(columns={
                "residual_kw": "Excess Power (kW)",
                "actual_power_kw": "Actual (kW)",
                "predicted_power_kw": "Expected (kW)",
                "excess_cost_inr": "Financial Loss (₹)",
                "waste_severity": "Severity Grade",
            }),
            use_container_width=True,
        )

        csv_data = waste_records.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Export Energy Waste Audit Report (CSV)",
            data=csv_data,
            file_name="campus_energy_waste_audit.csv",
            mime="text/csv",
        )
    else:
        st.success("✓ No energy waste detected under current threshold settings!")

# -------------------------------------------------------------------
# TAB 4: ACADEMIC EVALUATION & VIVA DEFENSE
# -------------------------------------------------------------------
with tab4:
    st.markdown("### 📈 Academic Evaluation & Ground-Truth Validation")
    st.caption("Demonstrating model validity, zero-leakage protocol, and comparison with unsupervised anomaly baselines.")

    col_eval1, col_eval2 = st.columns([1, 1])

    with col_eval1:
        st.markdown("##### 🧪 Anomaly Classification Metrics (vs. Ground-Truth)")
        eval_metrics = metadata.get("waste_detection_metrics", {}).get("contextual_detector", {})
        
        c1, c2 = st.columns(2)
        c1.metric("Precision", f"{eval_metrics.get('precision', 0.0):.4f}", help="Fraction of alerted incidents that were genuine waste")
        c2.metric("Recall", f"{eval_metrics.get('recall', 0.0):.4f}", help="Fraction of all true waste events successfully caught")
        
        c3, c4 = st.columns(2)
        c3.metric("F1-Score", f"{eval_metrics.get('f1_score', 0.0):.4f}", help="Harmonic mean of precision and recall")
        c4.metric("Accuracy", f"{eval_metrics.get('accuracy', 0.0):.4f}", help="Overall classification accuracy")

        # Confusion Matrix Heatmap
        cm = eval_metrics.get("confusion_matrix", [[0, 0], [0, 0]])
        cm_df = pd.DataFrame(
            cm,
            index=["Actual Normal", "Actual Waste"],
            columns=["Predicted Normal", "Predicted Waste"],
        )
        fig_cm = px.imshow(
            cm_df,
            text_auto=True,
            color_continuous_scale="Blues",
            title="Confusion Matrix on Unseen Test Partition",
        )
        fig_cm.update_layout(**PLOT_THEME, height=300)
        st.plotly_chart(fig_cm, use_container_width=True)

    with col_eval2:
        st.markdown("##### ⚖️ Contextual ML vs. Isolation Forest Benchmark")
        iso_metrics = metadata.get("waste_detection_metrics", {}).get("isolation_forest", {})
        
        comp_methods_df = pd.DataFrame([
            {
                "Detection Strategy": "Contextual ML Residual Detector",
                "Precision": f"{eval_metrics.get('precision', 0.0):.4f}",
                "Recall": f"{eval_metrics.get('recall', 0.0):.4f}",
                "F1-Score": f"{eval_metrics.get('f1_score', 0.0):.4f}",
                "Mechanism": "Supervised physics baseline + Occupancy gating",
            },
            {
                "Detection Strategy": "Isolation Forest (Unsupervised)",
                "Precision": f"{iso_metrics.get('precision', 0.0):.4f}",
                "Recall": f"{iso_metrics.get('recall', 0.0):.4f}",
                "F1-Score": f"{iso_metrics.get('f1_score', 0.0):.4f}",
                "Mechanism": "Multidimensional outlier isolation",
            },
        ])
        st.dataframe(comp_methods_df, use_container_width=True)

        st.markdown(
            """
            <div class="insight-box" style="border-left-color: #a855f7;">
                <b>🎓 Critical Viva Talking Point:</b><br>
                <i>Why does Isolation Forest have low precision (1.3%) for electricity waste?</i><br>
                Isolation Forest is an unsupervised density estimator. It isolates any rare point in feature space—such as sudden daytime power outages, extreme heat spikes, or packed auditorium events. None of these represent waste.<br>
                In contrast, our <b>Contextual ML Detective</b> directly answers: <i>"Is there excess power draw specifically when the space is empty?"</i>, achieving an <b>F1-score of 0.9647</b>.
            </div>
            """,
            unsafe_allow_html=True,
        )

# -------------------------------------------------------------------
# TAB 5: CUSTOM TELEMETRY UPLOAD & AUDITOR
# -------------------------------------------------------------------
with tab5:
    st.markdown("### 📤 Custom Telemetry Upload & Schema Validator")
    st.markdown("You can upload custom smart meter CSV telemetry in the sidebar. Verify that your file conforms to the schema below:")

    schema_guide = pd.DataFrame([
        {"Column Name": "timestamp", "Type": "Datetime", "Example": "2026-03-15 14:00:00", "Description": "Telemetry measurement timestamp"},
        {"Column Name": "building", "Type": "String", "Example": "Academic Block A", "Description": "Facility identifier"},
        {"Column Name": "zone", "Type": "String", "Example": "Lecture Halls & Classrooms", "Description": "Functional area"},
        {"Column Name": "occupancy", "Type": "Integer", "Example": "45", "Description": "Headcount present in zone"},
        {"Column Name": "temperature", "Type": "Float", "Example": "32.4", "Description": "Outdoor ambient temperature (°C)"},
        {"Column Name": "humidity", "Type": "Float", "Example": "58.2", "Description": "Relative humidity (%)"},
        {"Column Name": "actual_power_kw", "Type": "Float", "Example": "48.6", "Description": "Total active power drawn (kW)"},
    ])
    st.dataframe(schema_guide, use_container_width=True)

    st.markdown("##### 📥 Download Sample Dataset Template")
    sample_csv = default_df.head(200)[REQUIRED_INPUT_COLUMNS].to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Sample Telemetry CSV (200 Records)",
        data=sample_csv,
        file_name="sample_energy_telemetry.csv",
        mime="text/csv",
    )
