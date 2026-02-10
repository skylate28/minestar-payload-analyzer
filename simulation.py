import streamlit as st
import pandas as pd
import plotly.express as px
import time
from collections import Counter

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Minestar Live Simulation", layout="wide")

# --- CSS CUSTOM ---
st.markdown("""
<style>
    .big-font { font-size:20px !important; font-weight: bold; }
    .stAlert { padding: 10px; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: SETUP ---
st.sidebar.header("🛠️ Setup Simulasi")
uploaded_file = st.sidebar.file_uploader("Upload Data (Excel/CSV)", type=["xlsx", "csv"])

st.sidebar.subheader("Parameter Alert")
min_payload = st.sidebar.number_input("Min Payload (Ton)", value=90.0)
max_payload = st.sidebar.number_input("Max Payload (Ton)", value=120.0)
target_model = st.sidebar.text_input("Filter Model Unit", value="777")

st.sidebar.divider()
st.sidebar.subheader("⏯️ Kontrol Simulasi")
speed = st.sidebar.select_slider("Kecepatan Playback", options=["Slow", "Normal", "Fast", "Turbo"], value="Normal")

delay_map = {"Slow": 1.0, "Normal": 0.5, "Fast": 0.1, "Turbo": 0.01}
sleep_time = delay_map[speed]

start_btn = st.sidebar.button("▶️ MULAI SIMULASI", type="primary")

# --- JUDUL ---
st.title("🔴 Live Monitoring Simulation")
st.caption(f"Replay data operasional unit {target_model} secara real-time.")

# --- METRICS ---
col1, col2, col3 = st.columns(3)
metric_total = col1.empty()
metric_under = col2.empty()
metric_over = col3.empty()

st.divider()

# --- LAYOUT GRAFIK ---
# Kita bagi menjadi 2 baris
# Baris 1: Live Trend & Log
row1_col1, row1_col2 = st.columns([2, 1])
with row1_col1:
    st.subheader("📊 Live Payload Trend (Last 50 Trips)")
    chart_payload_placeholder = st.empty()
with row1_col2:
    st.subheader("🚨 Live Alert Log")
    log_placeholder = st.empty()

st.divider()

# Baris 2: Analisa Excavator (FITUR BARU)
st.subheader("🏗️ Top Excavator Underload Contributors")
chart_exca_placeholder = st.empty()

# --- LOGIC SIMULASI ---
if uploaded_file is not None and start_btn:
    try:
        # Baca File
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        # 1. Cleaning Data
        # Filter Data Sesuai Model
        df_clean = df[df['HaulModel'].astype(str).str.contains(target_model, case=False, na=False)].copy()
        
        # Urutkan berdasarkan OID atau Waktu
        if 'OID' in df_clean.columns:
            df_clean = df_clean.sort_values(by='OID')
        elif 'CycleHour' in df_clean.columns:
             df_clean = df_clean.sort_values(by='CycleHour')
        
        df_clean['PayloadAct'] = pd.to_numeric(df_clean['PayloadAct'], errors='coerce')
        df_clean = df_clean.dropna(subset=['PayloadAct']).reset_index(drop=True)

        if df_clean.empty:
            st.error(f"Tidak ditemukan data unit model '{target_model}' di file ini.")
            st.stop()

        # Wadah Data
        history_data = []
        underload_loaders = [] # List khusus untuk menampung nama Exca yang underload
        
        progress_bar = st.progress(0)
        total_rows = len(df_clean)
        
        # 2. LOOPING DATA
        for i in range(total_rows):
            row = df_clean.iloc[i]
            
            # Cek Status
            status = "NORMAL"
            color_code = "green"
            loader_name = str(row.get('LoadingEq', 'Unknown')) # Ambil nama Loader

            if row['PayloadAct'] < min_payload:
                status = "UNDERLOAD"
                color_code = "red"
                # Catat Exca yang bikin ulah
                underload_loaders.append(loader_name)
                
                # Toast Notification
                st.toast(f"⚠️ Underload! {row['HaulingEq']} by {loader_name} ({row['PayloadAct']} T)", icon="📉")
                
            elif row['PayloadAct'] > max_payload:
                status = "OVERLOAD"
                color_code = "orange"
            
            # Append History Utama
            row_data = {
                'Time': i, 
                'Unit': row['HaulingEq'],
                'Payload': row['PayloadAct'],
                'Status': status,
                'Loader': loader_name
            }
            history_data.append(row_data)
            df_hist = pd.DataFrame(history_data)
            
            # --- UPDATE DISPLAY ---
            
            # A. Metrics
            total = len(df_hist)
            under = len(df_hist[df_hist['Status'] == 'UNDERLOAD'])
            over = len(df_hist[df_hist['Status'] == 'OVERLOAD'])
            
            metric_total.metric("Total Trips", total)
            metric_under.metric("Underload", under, delta_color="inverse")
            metric_over.metric("Overload", over, delta_color="inverse")
            
            # B. Chart 1: Payload Trend (Bar Chart Unit)
            recent_data = df_hist.tail(50)
            fig_payload = px.bar(
                recent_data, 
                x="Unit", y="Payload", color="Status",
                color_discrete_map={'NORMAL': '#2ecc71', 'UNDERLOAD': '#e74c3c', 'OVERLOAD': '#f39c12'},
                range_y=[0, 160],
                hover_data=['Loader']
            )
            fig_payload.add_hline(y=min_payload, line_dash="dash", line_color="red")
            fig_payload.add_hline(y=max_payload, line_dash="dash", line_color="orange")
            chart_payload_placeholder.plotly_chart(fig_payload, use_container_width=True)
            
            # C. Chart 2: Top Exca Underload (Bar Chart Horizontal) - FITUR BARU
            if underload_loaders:
                # Hitung frekuensi underload per Exca
                exca_counts = Counter(underload_loaders)
                df_exca = pd.DataFrame.from_dict(exca_counts, orient='index', columns=['Count']).reset_index()
                df_exca.columns = ['Loader', 'Count']
                df_exca = df_exca.sort_values(by='Count', ascending=True) # Sort agar yang terbanyak di atas (di chart horizontal)

                fig_exca = px.bar(
                    df_exca, 
                    x="Count", y="Loader", 
                    orientation='h', 
                    text="Count",
                    color="Count",
                    color_continuous_scale="Reds",
                    title="Jumlah Kejadian Underload per Excavator"
                )
                fig_exca.update_layout(xaxis_title="Jumlah Underload", yaxis_title="Unit Excavator")
                chart_exca_placeholder.plotly_chart(fig_exca, use_container_width=True)
            else:
                chart_exca_placeholder.info("Belum ada kejadian Underload.")

            # D. Log Feed
            log_html = ""
            for _, log_row in df_hist.tail(5)[::-1].iterrows():
                icon = "✅" if log_row['Status'] == 'NORMAL' else "⚠️" if log_row['Status'] == 'UNDERLOAD' else "⛔"
                color = "green" if log_row['Status'] == 'NORMAL' else "red" if log_row['Status'] == 'UNDERLOAD' else "orange"
                log_html += f"""
                <div style="padding:5px; border-bottom:1px solid #ddd; font-size:14px;">
                    <span style="font-size:18px">{icon}</span> 
                    <b>{log_row['Unit']}</b> - <span style="color:{color}"><b>{log_row['Payload']} T</b></span> 
                    <span style="color:gray; font-size:12px">({log_row['Loader']})</span>
                </div>
                """
            log_placeholder.markdown(log_html, unsafe_allow_html=True)

            progress_bar.progress((i + 1) / total_rows)
            time.sleep(sleep_time)

        st.success("✅ Simulasi Selesai!")

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")

elif not uploaded_file:
    st.info("👈 Silahkan upload file data di sidebar.")
