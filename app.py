import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

# -------------------------------------------------------------
# 1. Page Configuration
# -------------------------------------------------------------
st.set_page_config(
    page_title="UAC Care Transition Analytics",
    page_icon="⚖️",
    layout="wide"
)

# -------------------------------------------------------------
# 2. Data Loading & KPI Computation (Self-Contained)
# -------------------------------------------------------------
@st.cache_data
def get_processed_data():
    # Detect data file automatically in root or data folder
    possible_paths = [
        'uac_processed.csv',
        'uac_processed.xls',
        'data/uac_processed.csv',
        'uac_raw_data.csv',
        'data/uac_raw_data.csv'
    ]
    
    file_path = None
    for p in possible_paths:
        if os.path.exists(p):
            file_path = p
            break
            
    if not file_path:
        st.error("⚠️ Data file not found in repository. Please ensure 'uac_processed.csv' or 'uac_raw_data.csv' is uploaded.")
        st.stop()
        
    # Read CSV or Excel
    if file_path.endswith('.xls') or file_path.endswith('.xlsx'):
        try:
            df = pd.read_excel(file_path)
        except Exception:
            df = pd.read_csv(file_path)
    else:
        df = pd.read_csv(file_path)
        
    df = df.dropna(how='all').reset_index(drop=True)
    
    # Clean headers
    df.columns = [c.replace('*', '').strip() for c in df.columns]
    
    # Rename if raw format
    rename_dict = {
        'Date': 'date',
        'Children apprehended and placed in CBP custody': 'cbp_intake',
        'Children in CBP custody': 'cbp_custody',
        'Children transferred out of CBP custody': 'cbp_transfers',
        'Children in HHS Care': 'hhs_custody',
        'Children discharged from HHS Care': 'hhs_discharges'
    }
    df = df.rename(columns=rename_dict)
    
    # Clean numbers if string
    num_cols = ['cbp_intake', 'cbp_custody', 'cbp_transfers', 'hhs_custody', 'hhs_discharges']
    for col in num_cols:
        if col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace(',', '').str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    # Date parse and sort
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    eps = 1e-6
    # Calculate KPIs if not already present
    if 'transfer_efficiency_ratio' not in df.columns:
        df['transfer_efficiency_ratio'] = df['cbp_transfers'] / (df['cbp_custody'] + eps)
    if 'discharge_effectiveness_index' not in df.columns:
        df['discharge_effectiveness_index'] = df['hhs_discharges'] / (df['hhs_custody'] + eps)
    if 'pipeline_throughput' not in df.columns:
        df['pipeline_throughput'] = df['hhs_discharges'] / (df['cbp_intake'] + eps)
    if 'daily_net_backlog' not in df.columns:
        df['daily_net_backlog'] = df['cbp_intake'] - df['hhs_discharges']
    if 'cumulative_backlog' not in df.columns:
        df['cumulative_backlog'] = df['daily_net_backlog'].cumsum()
        
    # Rolling metrics
    df['ter_7d_avg'] = df['transfer_efficiency_ratio'].rolling(7, min_periods=1).mean()
    df['dei_7d_avg'] = df['discharge_effectiveness_index'].rolling(7, min_periods=1).mean()
    
    # Outcome stability score (14-day rolling)
    roll_mean = df['discharge_effectiveness_index'].rolling(14, min_periods=3).mean()
    roll_std = df['discharge_effectiveness_index'].rolling(14, min_periods=3).std()
    df['outcome_stability_score'] = (1.0 - (roll_std / (roll_mean + eps))).clip(0.0, 1.0)
    
    df['day_of_week'] = df['date'].dt.day_name()
    df['year_month'] = df['date'].dt.to_period('M').astype(str)
    
    return df

df = get_processed_data()

# -------------------------------------------------------------
# 3. Sidebar Controls
# -------------------------------------------------------------
st.sidebar.title("🎛️ Control Panel")

# Date range selection
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

smooth_view = st.sidebar.checkbox("Show 7-Day Rolling Averages", value=True)

st.sidebar.subheader("🚨 Bottleneck Alert Trigger")
net_backlog_threshold = st.sidebar.slider(
    "Net Backlog Inflow Alert Threshold (Children/day)",
    min_value=0,
    max_value=150,
    value=40,
    step=5
)

# -------------------------------------------------------------
# 4. Header KPI Cards
# -------------------------------------------------------------
st.title("🛡️ UAC Care Pipeline & Transition Analytics")
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
# 5. Core Module Tabs
# -------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "🌊 Care Pipeline Flow",
    "⚡ Transition Efficiency Panels",
    "🚨 Bottleneck Detection",
    "📅 Temporal & Stability Analysis"
])

# TAB 1: Care Pipeline Flow
with tab1:
    st.subheader("1. Pipeline Volume Dynamics & Stage Movements")
    c1, c2 = st.columns([2, 1])
    with c1:
        fig_volume = go.Figure()
        fig_volume.add_trace(go.Scatter(x=f_df['date'], y=f_df['cbp_intake'], name="Daily Intake (CBP)", line=dict(color='#e74c3c', width=1.5)))
        fig_volume.add_trace(go.Scatter(x=f_df['date'], y=f_df['cbp_transfers'], name="Transfers (CBP -> HHS)", line=dict(color='#3498db', width=1.5)))
        fig_volume.add_trace(go.Scatter(x=f_df['date'], y=f_df['hhs_discharges'], name="Discharges (Sponsors)", line=dict(color='#2ecc71', width=1.5)))
        fig_volume.update_layout(title="Daily Movements Across Pipeline Stages", xaxis_title="Date", yaxis_title="Children / Day", hovermode="x unified")
        st.plotly_chart(fig_volume, use_container_width=True)
        
    with c2:
        tot_intake = f_df['cbp_intake'].sum()
        tot_transfers = f_df['cbp_transfers'].sum()
        tot_discharges = f_df['hhs_discharges'].sum()
        
        fig_sankey = go.Figure(data=[go.Sankey(
            node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5),
                      label=["Apprehensions", "CBP Custody Pool", "HHS Care Shelters", "Sponsor Reunification"],
                      color=["#e74c3c", "#f39c12", "#3498db", "#2ecc71"]),
            link=dict(source=[0, 1, 2], target=[1, 2, 3], value=[tot_intake, tot_transfers, tot_discharges])
        )])
        fig_sankey.update_layout(title_text="Total Movements (Selected Period)", height=400)
        st.plotly_chart(fig_sankey, use_container_width=True)

# TAB 2: Efficiency Panels
with tab2:
    st.subheader("2. Transition Efficiency Indicators")
    y_ter = 'ter_7d_avg' if smooth_view else 'transfer_efficiency_ratio'
    y_dei = 'dei_7d_avg' if smooth_view else 'discharge_effectiveness_index'
    
    col_a, col_b = st.columns(2)
    with col_a:
        fig_ter = px.line(f_df, x='date', y=y_ter, title=f"Transfer Efficiency Ratio (CBP → HHS) {'[7d Avg]' if smooth_view else ''}", color_discrete_sequence=['#2980b9'])
        st.plotly_chart(fig_ter, use_container_width=True)
    with col_b:
        fig_dei = px.line(f_df, x='date', y=y_dei, title=f"Discharge Effectiveness Index (HHS → Sponsor) {'[7d Avg]' if smooth_view else ''}", color_discrete_sequence=['#27ae60'])
        st.plotly_chart(fig_dei, use_container_width=True)

# TAB 3: Bottlenecks
with tab3:
    st.subheader("3. Bottleneck Identification & Threshold Violations")
    f_df['is_bottleneck_alert'] = f_df['daily_net_backlog'] >= net_backlog_threshold
    alert_count = int(f_df['is_bottleneck_alert'].sum())
    
    if alert_count > 0:
        st.error(f"⚠️ Threshold Alert: **{alert_count} days** experienced a net backlog >= **{net_backlog_threshold}** children/day.")
    else:
        st.success(f"✅ System Operating Normally: No dates exceeded the {net_backlog_threshold} backlog threshold.")
        
    fig_backlog = px.bar(
        f_df, x='date', y='daily_net_backlog',
        color='is_bottleneck_alert',
        color_discrete_map={True: '#e74c3c', False: '#95a5a6'},
        title="Net Daily Backlog (Intake - Discharges)"
    )
    fig_backlog.add_hline(y=net_backlog_threshold, line_dash="dot", line_color="red")
    st.plotly_chart(fig_backlog, use_container_width=True)
    
    fig_cum = px.area(f_df, x='date', y='cumulative_backlog', title="Cumulative Backlog Accumulation", color_discrete_sequence=['#8e44ad'])
    st.plotly_chart(fig_cum, use_container_width=True)

# TAB 4: Temporal & Stability
with tab4:
    st.subheader("4. Temporal Disparities & Placement Consistency")
    t1, t2 = st.columns(2)
    with t1:
        dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        dow_summary = f_df.groupby('day_of_week')[['cbp_transfers', 'hhs_discharges']].mean().reindex(dow_order).reset_index()
        fig_dow = px.bar(dow_summary, x='day_of_week', y=['cbp_transfers', 'hhs_discharges'], barmode='group', title="Mean Daily Movements by Day of Week")
        st.plotly_chart(fig_dow, use_container_width=True)
    with t2:
        fig_stab = px.line(f_df, x='date', y='outcome_stability_score', title="14-Day Placement Stability Score (1.0 = Highly Stable)", color_discrete_sequence=['#9b59b6'])
        fig_stab.add_hline(y=0.70, line_dash="dash", line_color="orange")
        st.plotly_chart(fig_stab, use_container_width=True)
