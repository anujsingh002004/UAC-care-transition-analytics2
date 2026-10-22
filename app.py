import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from data_pipeline import clean_and_process_uac_data

# -------------------------------------------------------------
# Application Setup & Theming
# -------------------------------------------------------------
st.set_page_config(
    page_title="UAC Care Transition Analytics",
    page_icon="⚖️",
    layout="wide"
)

# Custom CSS for polished government/executive layout
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #1f77b4;
    }
    .stAlert {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    return clean_and_process_uac_data('data/uac_raw_data.csv')

try:
    df = load_data()
except Exception as e:
    st.error(f"Error loading dataset: {e}. Please ensure 'data/uac_raw_data.csv' exists.")
    st.stop()

# -------------------------------------------------------------
# Sidebar: Controls & Capabilities (Guideline Requirement)
# -------------------------------------------------------------
st.sidebar.title("🎛️ Control Panel")

# 1. Date Range Selection
min_d, max_d = df['date'].min().date(), df['date'].max().date()
date_selection = st.sidebar.date_input(
    "Select Reporting Window",
    value=[min_d, max_d],
    min_value=min_d,
    max_value=max_d
)

if isinstance(date_selection, (list, tuple)) and len(date_selection) == 2:
    start_date, end_date = date_selection
    f_df = df[(df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)].copy()
else:
    f_df = df.copy()

# 2. Ratio-based Metric Toggles
st.sidebar.subheader("Metric Smoothing Options")
smooth_view = st.sidebar.checkbox("Show 7-Day Rolling Averages", value=True)

# 3. Threshold-based Alert Setting
st.sidebar.subheader("🚨 Bottleneck Alert Trigger")
net_backlog_threshold = st.sidebar.slider(
    "Net Backlog Inflow Alert Threshold (Children/day)",
    min_value=0,
    max_value=150,
    value=40,
    step=5
)

# -------------------------------------------------------------
# Top KPI Header (Guideline KPIs)
# -------------------------------------------------------------
st.title("🛡️ UAC Care Pipeline & Transition Efficiency Analytics")
st.caption("A process engineering lens on CBP custody handoffs, HHS shelter loads, and sponsor placement velocity.")

col1, col2, col3, col4, col5 = st.columns(5)

avg_ter = f_df['transfer_efficiency_ratio'].mean()
avg_dei = f_df['discharge_effectiveness_index'].mean()
avg_tp = f_df['pipeline_throughput'].mean()
net_backlog = f_df['daily_net_backlog'].sum()
avg_stability = f_df['outcome_stability_score'].mean()

col1.metric("Transfer Efficiency (TER)", f"{avg_ter:.1%}", help="Transfers out of CBP ÷ CBP Custody")
col2.metric("Discharge Effectiveness (DEI)", f"{avg_dei:.2%}", help="Discharges ÷ HHS Care load")
col3.metric("Throughput Rate", f"{avg_tp:.2f}x", help="Discharges ÷ Apprehensions (>1.0 clears backlog)")
col4.metric("Net Backlog Added", f"{net_backlog:+,.0f}", delta_color="inverse", help="Total Net Volume (Intake - Exits)")
col5.metric("Outcome Stability", f"{avg_stability:.2f}", help="Consistency score based on rolling CV (1.0 = Max stability)")

st.divider()

# -------------------------------------------------------------
# Core Modules in Tabs
# -------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "🌊 Care Pipeline Flow",
    "⚡ Transition Efficiency Panels",
    "🚨 Bottleneck Detection",
    "📅 Temporal & Stability Analysis"
])

# -------------------------------------------------------------
# TAB 1: Care Pipeline Flow Visualization
# -------------------------------------------------------------
with tab1:
    st.subheader("1. Pipeline Volume Dynamics & Custody Stocks")
    
    # Stage breakdown
    c1, c2 = st.columns([2, 1])
    with c1:
        fig_volume = go.Figure()
        fig_volume.add_trace(go.Scatter(x=f_df['date'], y=f_df['cbp_intake'], name="Daily Intake (CBP Apprehensions)", line=dict(color='#e74c3c', width=1.5)))
        fig_volume.add_trace(go.Scatter(x=f_df['date'], y=f_df['cbp_transfers'], name="Transfers (CBP -> HHS)", line=dict(color='#3498db', width=1.5)))
        fig_volume.add_trace(go.Scatter(x=f_df['date'], y=f_df['hhs_discharges'], name="Discharges (Sponsor Reunification)", line=dict(color='#2ecc71', width=1.5)))
        
        fig_volume.update_layout(
            title="Daily Flow Movements Through Pipeline Stages",
            xaxis_title="Date",
            yaxis_title="Daily Count of Children",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_volume, use_container_width=True)
    
    with c2:
        # Pipeline Sankey Snapshot (Aggregate for the period)
        tot_intake = f_df['cbp_intake'].sum()
        tot_transfers = f_df['cbp_transfers'].sum()
        tot_discharges = f_df['hhs_discharges'].sum()
        
        fig_sankey = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=["Apprehensions", "CBP Custody Pool", "HHS Care Shelters", "Sponsor Reunification"],
                color=["#e74c3c", "#f39c12", "#3498db", "#2ecc71"]
            ),
            link=dict(
                source=[0, 1, 2],
                target=[1, 2, 3],
                value=[tot_intake, tot_transfers, tot_discharges]
            )
        )])
        fig_sankey.update_layout(title_text="Total Stage Movements (Selected Window)", height=400)
        st.plotly_chart(fig_sankey, use_container_width=True)

# -------------------------------------------------------------
# TAB 2: Transfer & Discharge Efficiency Panels
# -------------------------------------------------------------
with tab2:
    st.subheader("2. Efficiency Velocity Indicators")
    
    y_ter = 'ter_7d_avg' if smooth_view else 'transfer_efficiency_ratio'
    y_dei = 'dei_7d_avg' if smooth_view else 'discharge_effectiveness_index'
    
    col_a, col_b = st.columns(2)
    with col_a:
        fig_ter = px.line(
            f_df, x='date', y=y_ter,
            title=f"Transfer Efficiency Ratio (CBP → HHS) {'[7-Day Avg]' if smooth_view else ''}",
            labels={y_ter: 'Efficiency Ratio'},
            color_discrete_sequence=['#2980b9']
        )
        fig_ter.add_hline(y=f_df[y_ter].mean(), line_dash="dash", line_color="gray", annotation_text="Period Average")
        st.plotly_chart(fig_ter, use_container_width=True)
        st.caption("Measures what proportion of children in CBP custody are transferred to HHS per day.")
        
    with col_b:
        fig_dei = px.line(
            f_df, x='date', y=y_dei,
            title=f"Discharge Effectiveness Index (HHS → Sponsor) {'[7-Day Avg]' if smooth_view else ''}",
            labels={y_dei: 'Effectiveness Index'},
            color_discrete_sequence=['#27ae60']
        )
        fig_dei.add_hline(y=f_df[y_dei].mean(), line_dash="dash", line_color="gray", annotation_text="Period Average")
        st.plotly_chart(fig_dei, use_container_width=True)
        st.caption("Measures the proportion of active HHS shelter residents placed with sponsors daily.")

# -------------------------------------------------------------
# TAB 3: Bottleneck Detection & Visual Alerts
# -------------------------------------------------------------
with tab3:
    st.subheader("3. Bottleneck Identification & Threshold Violations")
    
    # Flag alert days
    f_df['is_bottleneck_alert'] = f_df['daily_net_backlog'] >= net_backlog_threshold
    alert_count = f_df['is_bottleneck_alert'].sum()
    
    if alert_count > 0:
        st.error(f"⚠️ Threshold Alert: **{alert_count} days** experienced a net inflow backlog $\ge$ **{net_backlog_threshold}** children/day.")
    else:
        st.success(f"✅ System Operating Normally: No dates exceeded the {net_backlog_threshold} backlog threshold.")
    
    # Inflow vs Outflow Net Backlog Chart
    fig_backlog = px.bar(
        f_df, x='date', y='daily_net_backlog',
        color='is_bottleneck_alert',
        color_discrete_map={True: '#e74c3c', False: '#95a5a6'},
        labels={'daily_net_backlog': 'Net Inflow Imbalance', 'is_bottleneck_alert': 'Alert Triggered'},
        title=f"Net Daily Backlog Imbalance (Intake - Discharges)"
    )
    fig_backlog.add_hline(y=net_backlog_threshold, line_dash="dot", line_color="red", annotation_text="Threshold")
    fig_backlog.add_hline(y=0, line_color="black", line_width=1)
    st.plotly_chart(fig_backlog, use_container_width=True)
    
    # Cumulative backlog accumulation
    fig_cum = px.area(
        f_df, x='date', y='cumulative_backlog',
        title="Cumulative System Load Over Time",
        color_discrete_sequence=['#e67e22']
    )
    st.plotly_chart(fig_cum, use_container_width=True)

# -------------------------------------------------------------
# TAB 4: Temporal & Stability Analysis
# -------------------------------------------------------------
with tab4:
    st.subheader("4. Temporal Disparities & Outcome Stability")
    
    t_col1, t_col2 = st.columns(2)
    
    with t_col1:
        st.markdown("#### Weekday vs Weekend Operational Speed")
        dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        dow_summary = f_df.groupby('day_of_week')[['cbp_transfers', 'hhs_discharges']].mean().reindex(dow_order).reset_index()
        
        fig_dow = px.bar(
            dow_summary, x='day_of_week', y=['cbp_transfers', 'hhs_discharges'],
            barmode='group',
            title="Average Daily Movements by Day of Week",
            labels={'value': 'Average Children', 'day_of_week': 'Day of Week', 'variable': 'Stage Flow'}
        )
        st.plotly_chart(fig_dow, use_container_width=True)
        st.caption("Reveals administrative weekend drops in sponsor reunifications.")

    with t_col2:
        st.markdown("#### 14-Day Rolling Outcome Stability Score")
        fig_stab = px.line(
            f_df, x='date', y='outcome_stability_score',
            title="Placement Consistency Score (1.0 = Highly Stable, <0.7 = Volatile)",
            color_discrete_sequence=['#9b59b6']
        )
        fig_stab.add_hline(y=0.70, line_dash="dash", line_color="orange", annotation_text="Instability Warning (<0.70)")
        st.plotly_chart(fig_stab, use_container_width=True)
        st.caption("Calculated as 1 - CV(14-day DEI). Drops indicate sudden volatility in placement workflows.")

    # Month-over-Month Trends Table
    st.markdown("#### Month-over-Month Aggregated Performance")
    mom_table = f_df.groupby('year_month').agg(
        Total_Intake=('cbp_intake', 'sum'),
        Total_Transfers=('cbp_transfers', 'sum'),
        Total_Discharges=('hhs_discharges', 'sum'),
        Avg_Transfer_Efficiency=('transfer_efficiency_ratio', 'mean'),
        Avg_Discharge_Effectiveness=('discharge_effectiveness_index', 'mean')
    ).reset_index()
    
    st.dataframe(mom_table.style.format({
        'Avg_Transfer_Efficiency': '{:.2%}',
        'Avg_Discharge_Effectiveness': '{:.2%}',
        'Total_Intake': '{:,.0f}',
        'Total_Transfers': '{:,.0f}',
        'Total_Discharges': '{:,.0f}'
    }), use_container_width=True)