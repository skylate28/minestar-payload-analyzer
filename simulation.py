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

# --- LAYOUT DASHBOARD ---
# Kita bagi menjadi 2 Kolom Utama
# Kiri: Grafik Payload & Log Live
# Kanan: Leaderboard Exca (Tabel)

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("📊 Live Payload Trend")
    chart_payload_placeholder = st.empty()
    
    st.markdown("---")
    st.subheader("🚨 Live Alert Log")
    log_placeholder = st.empty()

with col_right:
    st.subheader("🏆 Top Exca Underload")
    st.caption("Daftar unit loading yang paling sering mengisi kurang.")
    # Placeholder untuk Tabel
    table_exca_placeholder = st.empty()

# --- LOGIC SIMULASI ---
if uploaded_file is not None and start_btn:
    try:
        # Baca File
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        # 1. Cleaning Data
        df_clean = df[df['HaulModel'].astype(str).str.contains(target_model, case=False, na=False)].copy()
        
        # Sort Data
        if 'OID' in df_clean.columns:
            df_clean = df_clean.sort_values(by='OID')
        elif 'CycleHour' in df_clean.columns:
             df_clean = df_clean.sort_values(by='CycleHour')
        
        df_clean['PayloadAct'] = pd.to_numeric(df_clean['PayloadAct'], errors='coerce')
        df_clean = df_clean.dropna(subset=['PayloadAct']).reset_index(drop=True)

        if df_clean.empty:
            st.error(f"Tidak ditemukan data unit model '{target_model}' di file ini.")
            st.stop()

        history_data = []
        underload_loaders = [] 
        
        progress_bar = st.progress(0)
        total_rows = len(df_clean)
        
        # 2. LOOPING DATA
        for i in range(total_rows):
            row = df_clean.iloc[i]
            
            # Cek Status
            status = "NORMAL"
            loader_name = str(row.get('LoadingEq', 'Unknown')) 

            if row['PayloadAct'] < min_payload:
                status = "UNDERLOAD"
                underload_loaders.append(loader_name)
                # Toast alert
                st.toast(f"⚠️ Underload! {row['HaulingEq']} by {loader_name} ({row['PayloadAct']} T)", icon="📉")
                
            elif row['PayloadAct'] > max_payload:
                status = "OVERLOAD"
            
            # Append History
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
            
            # B. Chart Payload (Kiri Atas)
            recent_data = df_hist.tail(40) # Tampilkan 40 trip terakhir
            fig_payload = px.bar(
                recent_data, 
                x="Unit", y="Payload", color="Status",
                color_discrete_map={'NORMAL': '#2ecc71', 'UNDERLOAD': '#e74c3c', 'OVERLOAD': '#f39c12'},
                range_y=[0, 160],
                hover_data=['Loader']
            )
            fig_payload.add_hline(y=min_payload, line_dash="dash", line_color="red")
            fig_payload.add_hline(y=max_payload, line_dash="dash", line_color="orange")
            fig_payload.update_layout(showlegend=False, margin=dict(l=0, r=0, t=0, b=0))
            
            chart_payload_placeholder.plotly_chart(fig_payload, use_container_width=True, key=f"payload_{i}")
            
            # C. Tabel Leaderboard Exca (Kanan) - FITUR UPDATE
            if underload_loaders:
                # Hitung frekuensi
                exca_counts = Counter(underload_loaders)
                df_exca = pd.DataFrame.from_dict(exca_counts, orient='index', columns=['Total Underload']).reset_index()
                df_exca.columns = ['Unit Exca', 'Total Underload']
                
                # Urutkan dari yang terbanyak (Ranking 1 di atas)
                df_exca = df_exca.sort_values(by='Total Underload', ascending=False).reset_index(drop=True)
                
                # Tampilkan Tabel dengan Highlight Warna Merah
                table_exca_placeholder.dataframe(
                    df_exca.style.background_gradient(subset=['Total Underload'], cmap='Reds'),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                table_exca_placeholder.info("Belum ada Underload.")

            # D. Log Feed (Kiri Bawah)
            log_html = ""
            for _, log_row in df_hist.tail(5)[::-1].iterrows():
                icon = "✅" if log_row['Status'] == 'NORMAL' else "⚠️" if log_row['Status'] == 'UNDERLOAD' else "⛔"
                color = "green" if log_row['Status'] == 'NORMAL' else "red" if log_row['Status'] == 'UNDERLOAD' else "orange"
                log_html += f"""
                <div style="padding:4px; border-bottom:1px solid #eee; font-size:13px;">
                    <span style="font-size:16px">{icon}</span> 
                    <b>{log_row['Unit']}</b> : <span style="color:{color}"><b>{log_row['Payload']} T</b></span> 
                    <i style="color:gray;">({log_row['Loader']})</i>
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
