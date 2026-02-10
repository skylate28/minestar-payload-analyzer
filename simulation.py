import streamlit as st
import pandas as pd
import plotly.express as px
import time

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Minestar Live Simulation", layout="wide")

# --- CSS CUSTOM UNTUK TAMPILAN LEBIH MODERN ---
st.markdown("""
<style>
    .big-font { font-size:20px !important; font-weight: bold; }
    .stAlert { padding: 10px; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: SETUP ---
st.sidebar.header("🛠️ Setup Simulasi")
uploaded_file = st.sidebar.file_uploader("Upload Data (CSV)", type=["csv"])

st.sidebar.subheader("Parameter Alert")
min_payload = st.sidebar.number_input("Min Payload (Ton)", value=90.0)
max_payload = st.sidebar.number_input("Max Payload (Ton)", value=120.0)
target_model = st.sidebar.text_input("Model Unit", value="777")

st.sidebar.divider()
st.sidebar.subheader("⏯️ Kontrol Simulasi")
speed = st.sidebar.select_slider("Kecepatan Playback", options=["Slow", "Normal", "Fast", "Turbo"], value="Normal")

# Mapping kecepatan ke delay (detik)
delay_map = {"Slow": 1.0, "Normal": 0.5, "Fast": 0.1, "Turbo": 0.01}
sleep_time = delay_map[speed]

start_btn = st.sidebar.button("▶️ MULAI SIMULASI", type="primary")

# --- JUDUL ---
st.title("🔴 Live Monitoring Simulation")
st.caption(f"Replay data operasional unit {target_model} seolah-olah terjadi saat ini.")

# --- PLACEHOLDER (Wadah Kosong untuk Diisi Nanti) ---
# Kita siapkan wadah kosong agar nanti bisa di-update tanpa refresh halaman
col1, col2, col3 = st.columns(3)
metric_total = col1.empty()
metric_under = col2.empty()
metric_over = col3.empty()

st.divider()

col_chart, col_log = st.columns([2, 1])

with col_chart:
    st.subheader("📊 Live Payload Trend")
    chart_placeholder = st.empty()

with col_log:
    st.subheader("🚨 Live Feed Log")
    log_placeholder = st.empty()

# --- LOGIC SIMULASI ---
if uploaded_file is not None and start_btn:
    # 1. Persiapan Data
    df = pd.read_csv(uploaded_file)
    
    # Filter Data Sesuai Model & Urutkan berdasarkan OID (agar kronologis)
    df_clean = df[df['HaulModel'].astype(str).str.contains(target_model, case=False, na=False)].copy()
    
    # Pastikan data terurut dari yang terlama ke terbaru
    if 'OID' in df_clean.columns:
        df_clean = df_clean.sort_values(by='OID')
    
    df_clean['PayloadAct'] = pd.to_numeric(df_clean['PayloadAct'], errors='coerce')
    df_clean = df_clean.dropna(subset=['PayloadAct']).reset_index(drop=True)

    # Wadah untuk menampung data yang "sudah terjadi"
    history_data = []
    
    # Progress Bar
    progress_bar = st.progress(0)
    
    # 2. LOOPING DATA (Jantung Simulasi)
    total_rows = len(df_clean)
    
    for i in range(total_rows):
        # Ambil satu baris data
        row = df_clean.iloc[i]
        
        # Tentukan Status
        status = "NORMAL"
        color_code = "green"
        if row['PayloadAct'] < min_payload:
            status = "UNDERLOAD"
            color_code = "red"
            # Munculkan Pop-up Toast jika Underload
            st.toast(f"⚠️ Alert! {row['HaulingEq']} Underload: {row['PayloadAct']} T", icon="📉")
        elif row['PayloadAct'] > max_payload:
            status = "OVERLOAD"
            color_code = "orange"
        
        # Masukkan ke history
        row_data = {
            'Time': i, # Kita pakai index sebagai sumbu X simulasi
            'Unit': row['HaulingEq'],
            'Payload': row['PayloadAct'],
            'Status': status,
            'Color': color_code,
            'Loader': row.get('LoadingEq', '-')
        }
        history_data.append(row_data)
        
        # Buat DataFrame sementara dari history
        df_hist = pd.DataFrame(history_data)
        
        # --- UPDATE TAMPILAN ---
        
        # 1. Update Metrics
        total = len(df_hist)
        under = len(df_hist[df_hist['Status'] == 'UNDERLOAD'])
        over = len(df_hist[df_hist['Status'] == 'OVERLOAD'])
        
        metric_total.metric("Total Trips", total)
        metric_under.metric("Underload (<90T)", under, delta_color="inverse")
        metric_over.metric("Overload (>120T)", over, delta_color="inverse")
        
        # 2. Update Chart (Hanya tampilkan 50 data terakhir agar grafik tidak berat)
        recent_data = df_hist.tail(50)
        
        fig = px.bar(
            recent_data, 
            x="Unit", 
            y="Payload", 
            color="Status",
            color_discrete_map={'NORMAL': '#2ecc71', 'UNDERLOAD': '#e74c3c', 'OVERLOAD': '#f39c12'},
            title=f"Last 50 Trips Payload (Live)",
            range_y=[0, 150] # Kunci sumbu Y agar tidak goyang
        )
        # Garis batas
        fig.add_hline(y=min_payload, line_dash="dash", line_color="red")
        fig.add_hline(y=max_payload, line_dash="dash", line_color="orange")
        
        chart_placeholder.plotly_chart(fig, use_container_width=True)
        
        # 3. Update Log Feed (Tampilkan 5 terbawah/terbaru)
        # Kita format HTML sederhana agar terlihat seperti log sistem
        log_html = ""
        for _, log_row in df_hist.tail(5)[::-1].iterrows(): # Loop terbalik (terbaru di atas)
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

        # Update Progress Bar
        progress_bar.progress((i + 1) / total_rows)
        
        # Jeda Waktu (Simulasi)
        time.sleep(sleep_time)

    st.success("✅ Simulasi Selesai!")

elif not uploaded_file:
    st.info("👈 Upload file CSV dulu di sidebar kiri.")