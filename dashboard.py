import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 0. PALET WARNA GLOBAL ---
COLOR_PRIMARY = '#0077B6'     # Biru Tua (Finansial, Positif)
COLOR_SECONDARY = '#4CC9F0'   # Biru Muda (Netral, Alternatif)
COLOR_RISK = '#E63946'        # Merah (Risiko, Default)
COLOR_WARNING = '#F7B731'     # Kuning/Oranye (Peringatan, Netral)
COLOR_LITERACY = '#38A3A5'    # Hijau/Aqua (Skor Kinerja/Literasi)

# --- 1. KONFIGURASI APLIKASI STREAMLIT ---
st.set_page_config(
    page_title="Dashboard Analisis Keuangan",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. MUAT DAN PRE-PROSES DATA ---

@st.cache_data
def load_and_preprocess_data():
    # Menggunakan nama file lengkap yang terdeteksi dari unggahan pengguna
    try:
        df_profile = pd.read_excel("profile_merged.xlsx", sheet_name=0)
    except FileNotFoundError:
        st.error("File 'profile_merged.xlsx - Sheet1.csv' tidak ditemukan. Pastikan file Excel tersedia.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), [], [], [], []
    
    try:
        df_regional = pd.read_excel("regional_filled_fix.xlsx", sheet_name=0)
    except FileNotFoundError:
        st.error("File 'regional_filled_fix.xlsx - Sheet1.csv' tidak ditemukan. Pastikan file Excel tersedia.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), [], [], [], []
        
    try:
        df_survey = pd.read_excel("survey_clean.xlsx", sheet_name=0)
    except FileNotFoundError:
        st.error("File 'survey_clean.xlsx - Sheet1.csv' tidak ditemukan. Pastikan file Excel tersedia.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), [], [], [], []


    # --- Preprocessing Regional Data ---
    regional_cols = {
        'Provinsi': 'Province',
        'Jumlah Dana yang Diberikan (Rp miliar)': 'Dana_Diberikan_M',
        'Outstanding Pinjaman (Rp miliar)': 'Outstanding_Pinjaman_M',
        'Jumlah Rekening Pemberi Pinjaman (akun)': 'Lender_Accounts',
        'Jumlah Rekening Penerima Pinjaman Aktif (entitas)': 'Borrower_Active_Entities',
        'TWP 90%': 'TWP_90',
        'Jumlah Penduduk (Ribu)': 'Population_K',
        'Pinjaman_per_Kapita': 'Loan_Per_Capita',
        'Efisiensi_P2P': 'P2P_Efficiency'
    }
    df_regional.rename(columns=regional_cols, inplace=True)

    # Menambahkan kelompok pulau (Jawa vs Non-Jawa)
    jawa_provinces = ['DKI Jakarta', 'Jawa Barat', 'Jawa Tengah', 'Jawa Timur', 'Banten', 'DI Yogyakarta']
    df_regional['Island_Group'] = df_regional['Province'].apply(lambda x: 'Jawa' if x in jawa_provinces else 'Non-Jawa')

    # --- Preprocessing Profile Data ---
    profile_cols = {
        'birth_year': 'Age', 
        'avg_monthly_income': 'Income_Status',
        'avg_monthly_expense': 'Expense_Status',
        'ewallet_spending': 'Ewallet_Spending_Status',
        'financial_anxiety_score': 'Anxiety_Score',
        'financial_literacy_score': 'Literacy_Score',
        'probability_default': 'Prob_Default',
        'default_label': 'Default_Label',
        'cluster': 'Cluster',
        'FWI_score': 'FWI_Score'
    }
    df_profile.rename(columns=profile_cols, inplace=True)

    # Hitung umur (asumsi tahun sekarang 2024)
    df_profile['Age'] = 2025 - df_profile['Age']

    # Konversi status ke numerik untuk perbandingan
    status_order = {'Sangat Rendah': 1, 'Rendah': 2, 'Menengah Rendah': 3, 'Menengah': 4, 'Menengah Tinggi': 5, 'Tinggi': 6}
    df_profile['Income_Status_Num'] = df_profile['Income_Status'].map(status_order)
    df_profile['Expense_Status_Num'] = df_profile['Expense_Status'].map(status_order)
    df_profile['Ewallet_Spending_Status_Num'] = df_profile['Ewallet_Spending_Status'].map(status_order)

    # --- Preprocessing Survey Data (Scoring Logic) ---
    
    # 1. Bersihkan nama kolom dari spasi yang tidak perlu
    df_survey.columns = df_survey.columns.str.strip()
    
    # PERBAIKAN: Mengganti nama kolom Provinsi_Bersih menjadi province untuk filtering
    rename_survey_cols = {
        'Provinsi_Bersih': 'province', # Perbaikan yang diminta
        'Pendidikan_Standar': 'Pendidikan', 
        'Perkiraan Pendapatan Bulanan_ID': 'Pendapatan',
        'Status Tempat Tinggal_ID': 'Status_Tinggal',
        'Status Pernikahan_ID': 'Status_Nikah',
        'Jenis Kelamin': 'Gender'
    }
    
    # Logic robust untuk menemukan kolom Pekerjaan
    job_col_found = False
    possible_job_cols = ['Jenis Pekerjaan_ID', 'Jenis Pekerjaan', 'Pekerjaan_ID', 'Pekerjaan']
    
    for col in possible_job_cols:
        if col in df_survey.columns:
            rename_survey_cols[col] = 'Pekerjaan'
            job_col_found = True
            break
        
    df_survey.rename(columns=rename_survey_cols, inplace=True)
    
    # Kolom kategori
    literasi_cols = [
        'Mampu Mengidentifikasi Risiko dan Memahami Angka Secara Kompleks', 
        'Mampu Mengenali Investasi Keuangan yang Baik', 
        'Mampu Memahami Makna di Balik Angka', 
        'Mampu Memahami Angka dan Ukuran Keuangan', 
        'Mampu Memahami Faktor yang Mempengaruhi Arus Kas dan Keuntungan', 
        'Mampu Memahami Laporan Keuangan dan Indikator Kinerja Utama Perusahaan'
    ]
    perilaku_cols = ['Mampu Mengatur dan Membagi Keuangan Sesuai Waktu dan Kebutuhan', 'Mampu Memperkirakan Ketersediaan Uang di Masa Depan', 'Ikut Merencanakan Pengeluaran Rumah Tangga', 'Selalu Berusaha Menabung untuk Hal yang Disukai', 'Menyarankan untuk Menyisihkan Uang untuk Keadaan Darurat', 'Memperhatikan Berita Ekonomi yang Dapat Mempengaruhi Keluarga']
    keputusan_cols_raw = ['Mampu Merencanakan agar Tidak Berbelanja Secara Impulsif', 'Memperhatikan Promosi dan Diskon', 'Berpikir Matang Sebelum Membeli Sesuatu', 'Suka Mencari Tahu Harga Sebelum Membeli', 'Sering Bertindak Tanpa Banyak Pertimbangan', 'Bersifat Impulsif', 'Sering Berbicara Tanpa Pikir Panjang', 'Mampu Menyesuaikan Keputusan Keuangan dengan Perubahan Situasi']
    kesejahteraan_cols_raw = ['Menjadi Keuangan Aman', 'Menjamin Keamanan Keuangan di Masa Depan', 'Akan Mencapai Tujuan Keuangan yang Telah Ditetapkan', 'Telah atau Akan Menabung Cukup untuk Hidup di Masa Depan', 'Merasa Tidak Akan Pernah Memiliki Hal yang Diinginkan karena Kondisi Keuangan', 'Tertinggal dalam Urusan Keuangan', 'Keuangan Mengendalikan Hidup Saya', 'Setiap Kali Merasa Mengendalikan Keuangan, Selalu Ada Halangan', 'Tidak Dapat Menikmati Hidup karena Terlalu Terobsesi dengan Uang']

    reverse_cols = [
        'Sering Bertindak Tanpa Banyak Pertimbangan',
        'Bersifat Impulsif',
        'Sering Berbicara Tanpa Pikir Panjang',
        'Merasa Tidak Akan Pernah Memiliki Hal yang Diinginkan karena Kondisi Keuangan',
        'Tertinggal dalam Urusan Keuangan',
        'Keuangan Mengendalikan Hidup Saya',
        'Setiap Kali Merasa Mengendalikan Keuangan, Selalu Ada Halangan',
        'Tidak Dapat Menikmati Hidup karena Terlalu Terobsesi dengan Uang'
    ]

    all_score_cols_raw = literasi_cols + perilaku_cols + keputusan_cols_raw + kesejahteraan_cols_raw
    
    # Konversi ke float sebelum reverse scoring
    for col in all_score_cols_raw:
        if col in df_survey.columns:
            df_survey[col] = pd.to_numeric(df_survey[col], errors='coerce').astype(float)

    # Reverse Scoring
    keputusan_cols = keputusan_cols_raw.copy()
    kesejahteraan_cols = kesejahteraan_cols_raw.copy()

    for col in reverse_cols:
        if col in df_survey.columns:
            # Skor dibalik = 6 - Skor (Asumsi skala 1-5)
            df_survey[f'{col}_R'] = 6 - df_survey[col]
            
            # Ganti kolom asli dengan kolom _R di daftar kategori
            if col in keputusan_cols:
                keputusan_cols.remove(col)
                keputusan_cols.append(f'{col}_R')
            if col in kesejahteraan_cols:
                kesejahteraan_cols.remove(col)
                kesejahteraan_cols.append(f'{col}_R')

    # Hitung Skor Komposit
    valid_literasi_cols = [col for col in literasi_cols if col in df_survey.columns]
    valid_perilaku_cols = [col for col in perilaku_cols if col in df_survey.columns]
    valid_keputusan_cols = [col for col in keputusan_cols if col in df_survey.columns]
    valid_kesejahteraan_cols = [col for col in kesejahteraan_cols if col in df_survey.columns]

    df_survey['Skor_Literasi'] = df_survey[valid_literasi_cols].mean(axis=1)
    df_survey['Skor_Perilaku'] = df_survey[valid_perilaku_cols].mean(axis=1)
    df_survey['Skor_Keputusan'] = df_survey[valid_keputusan_cols].mean(axis=1)
    df_survey['Skor_Kesejahteraan'] = df_survey[valid_kesejahteraan_cols].mean(axis=1)
    
    # Cek dan isi kolom Pekerjaan jika tidak ditemukan
    if 'Pekerjaan' not in df_survey.columns:
         df_survey['Pekerjaan'] = 'N/A'
         st.warning("Kolom 'Pekerjaan' tidak ditemukan di data Survei. Chart terkait Pekerjaan mungkin menampilkan 'N/A'.")


    return df_profile, df_regional, df_survey, valid_literasi_cols, valid_perilaku_cols, valid_keputusan_cols, valid_kesejahteraan_cols

# Menjalankan fungsi pemuatan data
try:
    df_profile, df_regional, df_survey, literasi_cols, perilaku_cols, keputusan_cols, kesejahteraan_cols = load_and_preprocess_data()
except Exception as e:
    st.error(f"Terjadi kesalahan saat memuat atau memproses data: {e}")
    # Menghentikan eksekusi Streamlit jika terjadi kesalahan fatal pada pemuatan data
    st.stop()


# --- 3. FUNGSI CARD KPI ---
def kpi_card(title, value, unit="", delta=None):
    # PERBAIKAN UTAMA: Konversi nilai string (value) ke float untuk perbandingan numerik
    # Menangani koma pada Total Users dengan menghapus koma terlebih dahulu
    value_clean = str(value).replace(',', '')
    
    try:
        numeric_value = float(value_clean)
    except ValueError:
        numeric_value = 0 # Default jika konversi gagal 
        
    color = COLOR_PRIMARY
    icon = "📊"
    
    if "Default Rate" in title:
        # Default Rate: Baik jika nilainya rendah (dibawah 5%)
        color = COLOR_RISK if numeric_value > 5 else COLOR_LITERACY
        icon = "🚨"
    elif "Anxiety Score" in title:
        # Anxiety Score: Baik jika nilainya rendah
        color = COLOR_RISK if numeric_value > 3 else COLOR_LITERACY
        icon = "😟"
    elif "Literacy Score" in title or "FWI Score" in title:
        # Literacy/FWI Score: Baik jika nilainya tinggi (di atas 3.5 dari skala 5, atau di atas 70 dari skala 100)
        threshold = 3.5 if unit == "" else 70 
        color = COLOR_LITERACY if numeric_value > threshold else COLOR_WARNING
        icon = "💡"
    elif "Total Users" in title:
        icon = "👥"
        color = COLOR_PRIMARY
    
    # Penentuan warna dan ikon untuk Cluster
    if "Cluster" in title:
        if "Cluster 0" in title:
            color = COLOR_LITERACY
            icon = "✅"
        elif "Cluster 1" in title:
            color = COLOR_WARNING
            icon = "⚠️"
        elif "Cluster 2" in title:
            color = COLOR_RISK
            icon = "🛑"
        
    delta_display = ""
    delta_color = COLOR_PRIMARY
    if delta:
        if "Default Rate" in title and delta == "Target < 5%":
            is_good = numeric_value < 5
            icon_delta = "▼" if numeric_value > 5 else "▲"
            delta_color = COLOR_LITERACY if is_good else COLOR_RISK
            delta_display = f'<span style="color: {delta_color}; font-size: 12px;">{icon_delta} {delta}</span>'
        else:
            delta_display = f'<span style="color: {COLOR_PRIMARY}; font-size: 12px;">{delta}</span>'
            
    st.markdown(f"""
        <div style="
            padding: 15px; 
            border-radius: 12px; 
            text-align: left; 
            background-color: #FFFFFF; 
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            border-left: 5px solid {color};
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <p style="font-size: 14px; color: #6C757D; margin: 0; font-weight: bold;">{title}</p>
                <span style="font-size: 20px; color: {color};">{icon}</span>
            </div>
            <h3 style="font-size: 32px; color: #343A40; margin-top: 10px; margin-bottom: 5px; font-weight: 700;">{value} {unit}</h3>
            {delta_display}
        </div>
    """, unsafe_allow_html=True)


# --- 4. HALAMAN REGIONAL ---

def page_regional(df):
    st.title("🗺️ Analisis Regional ")
    st.write("Analisis distribusi dana dan risiko pinjaman berdasarkan provinsi dan kelompok pulau.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Distribusi Dana Diberikan (Rp Miliar)")
        df_dana = df.groupby('Island_Group')['Dana_Diberikan_M'].sum().reset_index()
        fig_dana = px.pie(
            df_dana,
            values='Dana_Diberikan_M',
            names='Island_Group',
            title='Dana Diberikan',
            hole=0.4, # Sedikit lebih besar dari Donut
            color='Island_Group',
            color_discrete_map={'Jawa': COLOR_PRIMARY, 'Non-Jawa': COLOR_SECONDARY},
            template='plotly_white'
        )
        # Menambahkan font Poppins ke Plotly
        fig_dana.update_layout(font=dict(family='Poppins', size=12))
        st.plotly_chart(fig_dana, use_container_width=True)

    with col2:
        st.subheader("Proporsi Outstanding Pinjaman (Rp Miliar)")
        df_outstanding = df.groupby('Island_Group')['Outstanding_Pinjaman_M'].sum().reset_index()
        fig_outstanding = px.pie(
            df_outstanding,
            values='Outstanding_Pinjaman_M',
            names='Island_Group',
            title='Outstanding Pinjaman',
            hole=0.4,
            color='Island_Group',
            color_discrete_map={'Jawa': COLOR_PRIMARY, 'Non-Jawa': COLOR_SECONDARY},
            template='plotly_white'
        )
        # Menambahkan font Poppins ke Plotly
        fig_outstanding.update_layout(font=dict(family='Poppins', size=12))
        st.plotly_chart(fig_outstanding, use_container_width=True)
    
    st.markdown("---")

    st.subheader("Dana Diberikan vs Outstanding Pinjaman (Rp Miliar) per Provinsi")
    df_stack = df.melt(
        id_vars='Province', 
        value_vars=['Dana_Diberikan_M', 'Outstanding_Pinjaman_M'], 
        var_name='Tipe_Dana', 
        value_name='Nilai_M'
    ).sort_values(by='Nilai_M', ascending=False)
    
    # Sort the provinces by the total value for better visualization
    province_order = df_stack.groupby('Province')['Nilai_M'].sum().sort_values(ascending=False).index.tolist()

    chart_stack = alt.Chart(df_stack).mark_bar().encode(
        x=alt.X('Province', sort=province_order, title="Provinsi"),
        y=alt.Y('Nilai_M', title="Nilai (Rp Miliar)"),
        # WARNA HIJAU/KUNING (Sesuai permintaan Anda)
        color=alt.Color('Tipe_Dana', scale=alt.Scale(domain=['Dana_Diberikan_M', 'Outstanding_Pinjaman_M'], range=[COLOR_WARNING, COLOR_LITERACY]),
            legend=alt.Legend(title="Tipe Dana", labelExpr="datum.label == 'Dana_Diberikan_M' ? 'Diberikan' : 'Outstanding'")),
        tooltip=['Province', 'Tipe_Dana', alt.Tooltip('Nilai_M', format='.2f')]
    ).properties(
        title="Perbandingan Dana Diberikan dan Outstanding Pinjaman"
    ).interactive().configure_text(font='Poppins') # Menambahkan Poppins di Altair
    st.altair_chart(chart_stack, use_container_width=True)

    st.markdown("---")

    col3, col4 = st.columns(2)

    # --- RASIO LENDER/BORROWER SEJATI ---
    with col3:
        st.subheader("TOP 10 Rasio Lender-Borrower ")
        
        # 1. Hitung Rasio Lender/Borrower (Lender Accounts / Borrower Active Entities)
        # Menambahkan epsilon untuk menghindari pembagian dengan nol
        df['Lender_Borrower_Ratio'] = df['Lender_Accounts'] / (df['Borrower_Active_Entities'] + 1e-6)
        
        # 2. Ambil 10 Provinsi Teratas
        df_top_ratio = df.sort_values('Lender_Borrower_Ratio', ascending=False).head(10)
        
        # 3. Visualisasi Bar Chart Horizontal
        chart_ratio = alt.Chart(df_top_ratio).mark_bar().encode(
            x=alt.X('Lender_Borrower_Ratio', title="Rasio Lender-Borrower"),
            y=alt.Y('Province', sort='-x', title="Provinsi"),
            color=alt.value(COLOR_PRIMARY),
            tooltip=['Province', alt.Tooltip('Lender_Borrower_Ratio', format='.2f')]
        ).properties(
            title="10 Provinsi dengan Rasio Lender-Borrower Tertinggi"
        ).interactive().configure_text(font='Poppins') # Menambahkan Poppins di Altair
        
        st.altair_chart(chart_ratio, use_container_width=True)

    with col4:
        st.subheader("TWP 90% Tertinggi (Risiko Kredit)")
        # TWP 90%
        df_top_twp = df.sort_values('TWP_90', ascending=False).head(10)
        chart_twp = alt.Chart(df_top_twp).mark_bar().encode(
            x=alt.X('TWP_90', title="TWP 90% (Default Rate)"),
            y=alt.Y('Province', sort='-x', title="Provinsi"),
            color=alt.value(COLOR_RISK),
            tooltip=['Province', alt.Tooltip('TWP_90', format='.3f')]
        ).properties(
            title="10 Provinsi dengan TWP 90% Tertinggi"
        ).interactive().configure_text(font='Poppins') # Menambahkan Poppins di Altair
        st.altair_chart(chart_twp, use_container_width=True)

# --- 5. HALAMAN PROFILE ---

def page_profile(df):
    st.title("👤 Analisis Profil Pengguna & Fintech")
    st.write("Eksplorasi demografi, perilaku, dan skor keuangan pengguna")
    
    # --- Filter Provinsi (Dipindahkan ke sini) ---
    st.sidebar.subheader("Filter Profil")
    all_provinces = ['Semua Provinsi'] + sorted(df['province'].unique().tolist())
    selected_province = st.sidebar.selectbox("Pilih Provinsi untuk Profil", all_provinces, key="profile_province_filter")

    if selected_province != 'Semua Provinsi':
        df_filtered = df[df['province'] == selected_province]
    else:
        df_filtered = df
    st.markdown("---")

    # --- KPI Cards ---
    st.subheader("Key Performance Indicators")
    
    if not df_filtered.empty:
        col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)
        
        total_users = df_filtered.shape[0]
        default_rate = df_filtered['Default_Label'].mean() * 100
        mean_anxiety = df_filtered['Anxiety_Score'].mean()
        mean_literacy = df_filtered['Literacy_Score'].mean()
        mean_fwi = df_filtered['FWI_Score'].mean()

        with col_kpi1: kpi_card("Total Users", f"{total_users:,}")
        with col_kpi2: kpi_card("Default Rate", f"{default_rate:.2f}", "%", delta="Target < 5%")
        with col_kpi3: kpi_card("Avg. Anxiety Score", f"{mean_anxiety:.2f}")
        with col_kpi4: kpi_card("Avg. Literacy Score", f"{mean_literacy:.2f}")
        with col_kpi5: kpi_card("Avg. FWI Score", f"{mean_fwi:.2f}")

        st.markdown("---")

        # --- Donut Chart (Gender & Investment Type) ---
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.subheader("Proporsi Gender")
            gender_data = df_filtered['gender'].value_counts().reset_index()
            gender_data.columns = ['Gender', 'Count']
            fig_gender = px.pie(gender_data, values='Count', names='Gender', hole=0.4, 
                                color_discrete_sequence=[COLOR_PRIMARY, COLOR_SECONDARY],
                                title='Jumlah Gender', template='plotly_white')
            fig_gender.update_layout(font=dict(family='Poppins', size=12))
            st.plotly_chart(fig_gender, use_container_width=True)

        # PERBAIKAN: Investment Type dalam satu tone warna
        with col_chart2:
            st.subheader("Proporsi Investment Type")
            invest_data = df_filtered['investment_type'].value_counts().reset_index()
            invest_data.columns = ['Investment_Type', 'Count']
            # Menggunakan skema multi-warna berdasarkan satu tone (PRIMARY)
            color_seq_single = px.colors.sequential.PuBu[3:] 
            fig_invest = px.pie(invest_data, values='Count', names='Investment_Type', hole=0.4, 
                                color_discrete_sequence=color_seq_single,
                                title='Jumlah Investment Type', template='plotly_white')
            fig_invest.update_layout(font=dict(family='Poppins', size=12))
            st.plotly_chart(fig_invest, use_container_width=True)
            
        st.markdown("---")

        # --- Histogram (Age & Probability Default) ---
        col_hist1, col_hist2 = st.columns(2)

        with col_hist1:
            st.subheader("Distribusi Usia (Age)")
            chart_age = alt.Chart(df_filtered).mark_bar().encode(
                x=alt.X('Age', bin=alt.Bin(maxbins=20), title="Usia"),
                y=alt.Y('count()', title="Jumlah Pengguna"),
                tooltip=['Age', 'count()'],
                color=alt.value(COLOR_PRIMARY)
            ).properties(title="Histogram Usia").interactive().configure_text(font='Poppins')
            st.altair_chart(chart_age, use_container_width=True)

        # PERBAIKAN: Distribution Probability plot dalam satu tone warna (RISK)
        with col_hist2:
            st.subheader("Distribusi Probability Default")
            chart_prob = alt.Chart(df_filtered).mark_bar().encode(
                x=alt.X('Prob_Default', bin=alt.Bin(maxbins=20), title="Probabilitas Default"),
                y=alt.Y('count()', title="Jumlah Pengguna"),
                color=alt.value(COLOR_RISK)
            ).properties(title="Histogram Probabilitas Default").interactive().configure_text(font='Poppins')
            st.altair_chart(chart_prob, use_container_width=True)

        st.markdown("---")
        
        # --- Bar & Column Chart (Income vs Expense & E-Wallet Spending) ---
        col_inc_exp, col_ewallet = st.columns(2)
        
        # PERBAIKAN: Status Pendapatan vs. Pengeluaran (Cluster Bar Chart yang diperbaiki)
        with col_inc_exp:
            st.subheader("Rata-Rata Status Pendapatan vs Pengeluaran")
            df_inc_exp = df_filtered.groupby('Income_Status')[['Income_Status_Num', 'Expense_Status_Num']].mean().reset_index()
            df_inc_exp_melt = df_inc_exp.melt(id_vars='Income_Status', var_name='Metric', value_name='Avg_Status_Num')
            
            status_labels = ['Sangat Rendah', 'Rendah', 'Menengah Rendah', 'Menengah', 'Menengah Tinggi', 'Tinggi']
            
            # Cluster Bar Chart yang benar-benar berkelompok
            chart_inc_exp = alt.Chart(df_inc_exp_melt).mark_bar().encode(
                # X: Kategori utama (Income Status)
                x=alt.X('Income_Status:N', title="Status Pendapatan", sort=status_labels),
                # Y: Nilai (Tinggi bar)
                y=alt.Y('Avg_Status_Num', title="Rata-Rata Status (1-6)"),
                
                # Color: Metric digunakan untuk membedakan Pendapatan vs Pengeluaran
                color=alt.Color('Metric', scale=alt.Scale(domain=['Income_Status_Num', 'Expense_Status_Num'], range=[COLOR_PRIMARY, COLOR_RISK]), 
                                                          legend=alt.Legend(title="Metrik Status", labelExpr="datum.label == 'Income_Status_Num' ? 'Pendapatan' : 'Pengeluaran'")),
                
                # XOffset untuk menggeser bar di dalam band X (Clustering)
                xOffset=alt.XOffset('Metric', scale=alt.Scale(domain=['Income_Status_Num', 'Expense_Status_Num'])),
                
                tooltip=['Income_Status', alt.Tooltip('Metric', title='Metrik Status', format='.2f'), alt.Tooltip('Avg_Status_Num', title='Rata-Rata Status', format='.2f')]
            ).properties(
                title="Rata-Rata Status Pengeluaran vs Pendapatan"
            ).interactive().configure_text(font='Poppins')
            st.altair_chart(chart_inc_exp, use_container_width=True)

        # 2. Jumlah E-Wallet Spending berdasarkan Status
        with col_ewallet:
            st.subheader("Distribusi Jumlah E-Wallet Spending")
            df_ewallet = df_filtered.groupby('Ewallet_Spending_Status')['Ewallet_Spending_Status'].count().reset_index(name='Count')
            
            chart_ewallet = alt.Chart(df_ewallet).mark_bar().encode(
                x=alt.X('Ewallet_Spending_Status', title="Status E-Wallet Spending"),
                y=alt.Y('Count', title="Jumlah Pengguna"),
                color=alt.value(COLOR_WARNING),
                tooltip=['Ewallet_Spending_Status', 'Count']
            ).properties(title="Distribusi E-Wallet Spending").interactive().configure_text(font='Poppins')
            st.altair_chart(chart_ewallet, use_container_width=True)

        st.markdown("---")

        # --- Stacked Bar Chart (Education vs Employment) ---
        st.subheader("Proporsi Pendidikan Berdasarkan Status Pekerjaan")
        chart_stacked = alt.Chart(df_filtered).mark_bar().encode(
            x=alt.X('employment_status', title="Status Pekerjaan"),
            y=alt.Y('count()', stack="normalize", title="Proporsi"),
            color=alt.Color('education_level', title="Level Pendidikan", scale=alt.Scale(scheme='viridis')), # Menggunakan palet Viridis untuk kontras yang baik
            tooltip=['employment_status', 'education_level', alt.Tooltip('count()', title='Jumlah', format=',')]
        ).properties(title="Proporsi Pendidikan Berdasarkan Status Pekerjaan").interactive().configure_text(font='Poppins')
        st.altair_chart(chart_stacked, use_container_width=True)
        
        st.markdown("---")

        # --- Treemap (Main Fintech App & Loan Usage Purpose) ---
        col_tree1, col_tree2 = st.columns(2)

        # Treemap Main Fintech App (Satu Tone Biru, dari gelap ke terang)
        with col_tree1:
            st.subheader("Distribusi Main Fintech App")
            df_fintech = df_filtered['main_fintech_app'].value_counts().reset_index()
            df_fintech.columns = ['Fintech_App', 'Count']
            fig_fintech_tree = px.treemap(
                df_fintech,
                path=['Fintech_App'],
                values='Count',
                color='Count',  # Menggunakan Count untuk menentukan warna
                color_continuous_scale='Blues', # Skema warna sequential Biru
                title="Main Fintech App",
                template='plotly_white'
            )
            fig_fintech_tree.update_layout(margin=dict(t=50, l=10, r=10, b=10), font=dict(family='Poppins', size=12))
            st.plotly_chart(fig_fintech_tree, use_container_width=True)

        # Treemap Loan Usage Purpose (Satu Tone Hijau, dari gelap ke terang)
        with col_tree2:
            st.subheader("Distribusi Loan Usage Purpose")
            df_loan = df_filtered['loan_usage_purpose'].value_counts().reset_index()
            df_loan.columns = ['Purpose', 'Count']
            fig_loan_tree = px.treemap(
                df_loan,
                path=['Purpose'],
                values='Count',
                color='Count',  # Menggunakan Count untuk menentukan warna
                color_continuous_scale='Greens', # Skema warna sequential Hijau
                title="Loan Usage Purpose",
                template='plotly_white'
            )
            fig_loan_tree.update_layout(margin=dict(t=50, l=10, r=10, b=10), font=dict(family='Poppins', size=12))
            st.plotly_chart(fig_loan_tree, use_container_width=True)

        st.markdown("---")
        
        # --- Gauge Chart (Average FWI Score) & Cluster KPI ---
        col_gauge, col_cluster_kpis = st.columns([1, 1])

        # FWI Score (Gauge Chart Angular/Speedometer)
        with col_gauge:
            st.subheader("Rata-Rata FWI Score (Financial Well-being Index)")
            
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = mean_fwi,
                title = {'text': "Average FWI Score"},
                gauge = {
                    'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkgray"},
                    'shape': "angular", # Memastikan bentuk semi-circle
                    'bar': {'color': 'rgba(0,0,0,0)'}, # Menghilangkan bar nilai (menggunakan jarum)
                    'steps': [
                        {'range': [0, 20], 'color': COLOR_RISK},        # Merah
                        {'range': [20, 40], 'color': '#F4A261'},       # Oranye
                        {'range': [40, 60], 'color': COLOR_WARNING},     # Kuning
                        {'range': [60, 80], 'color': '#A7C957'},       # Hijau Muda
                        {'range': [80, 100], 'color': COLOR_LITERACY}    # Hijau Tua
                    ],
                    'threshold': {
                        'line': {'color': "black", 'width': 6}, # Jarum penunjuk
                        'thickness': 0.9,
                        'value': mean_fwi
                    }
                }
            ))
            fig_gauge.update_layout(height=300, template='plotly_white', margin=dict(t=80, b=40), font=dict(family='Poppins', size=12))
            st.plotly_chart(fig_gauge, use_container_width=True)

        # Clusterisasi dalam 3 KPI cards
        with col_cluster_kpis:
            st.subheader("Jumlah Users per Cluster")
            cluster_counts = df_filtered['Cluster'].value_counts().sort_index()
            
            # Bar chart untuk visualisasi cluster
            df_cluster_counts = cluster_counts.reset_index()
            df_cluster_counts.columns = ['Cluster', 'Count']
            
            chart_cluster_bar = alt.Chart(df_cluster_counts).mark_bar().encode(
                x=alt.X('Cluster:N', title="Cluster ID"),
                y=alt.Y('Count', title="Jumlah Pengguna"),
                color=alt.Color('Cluster:N', scale=alt.Scale(domain=[0, 1, 2], range=[COLOR_LITERACY, COLOR_WARNING, COLOR_RISK]), legend=None),
                tooltip=['Cluster:N', 'Count']
            ).properties(title="Jumlah User per Cluster").interactive().configure_text(font='Poppins')
            st.altair_chart(chart_cluster_bar, use_container_width=True)

            # KPI Cards untuk Cluster
            col_c0, col_c1, col_c2 = st.columns(3)
            with col_c0:
                kpi_card("Cluster 0 Mahasiswa yang Stabil Dengan Kecemasan Rendah", f"{cluster_counts.get(0, 0):,}")
            with col_c1:
                kpi_card("Cluster 1 Mahasiswa Dengan Kecemasan Finansial Tinggi dan Pengeluaran Menengah", f"{cluster_counts.get(1, 0):,}")
            with col_c2:
                kpi_card("Cluster 2 Pelajar Dengan Kecemasan Finansial Sedang & Pola Pengeluaran Stabil", f"{cluster_counts.get(2, 0):,}")

    else:
        st.warning("Tidak ada data untuk provinsi yang dipilih.")


# --- 6. HALAMAN SURVEY ---

def page_survey(df):
    st.title("📊 Analisis Skor Komposit Survei Keuangan")
    st.write("Analisis mendalam skor Literasi, Perilaku, Keputusan, dan Kesejahteraan Keuangan berdasarkan demografi.")
    
    # --- Filter Provinsi untuk Survey (Dipindahkan ke sini) ---
    st.sidebar.subheader("Filter Survey")
    all_provinces = ['Semua Provinsi'] + sorted(df['province'].unique().tolist())
    selected_province = st.sidebar.selectbox("Pilih Provinsi untuk Survei", all_provinces, key="survey_province_filter")
    
    if selected_province != 'Semua Provinsi':
        df_filtered = df[df['province'] == selected_province]
    else:
        df_filtered = df
        
    st.markdown("---")
    
    # --- Filter/Navigasi Indeks ---
    st.sidebar.subheader("Pilih Indeks Survei")
    selected_index = st.sidebar.radio(
        "Indeks yang Diinginkan",
        ['Indeks Literasi Keuangan', 'Indeks Perilaku Keuangan', 'Indeks Gaya Keputusan & Impulsif', 'Indeks Kesejahteraan Keuangan'],
        key="survey_index_radio" # Mengganti key untuk menghindari konflik
    )
    st.header(f"Fokus Analisis: {selected_index}")
    st.markdown("---")
    
    # Mendefinisikan urutan kategori untuk plot yang lebih baik
    pendidikan_order = ['SD', 'SMP', 'SMA', 'D1/D3', 'S1/D4', 'S2/S3']
    pendapatan_order = sorted(df_filtered['Pendapatan'].unique())
    pekerjaan_order = sorted(df_filtered['Pekerjaan'].unique())


    # Helper function for pivot table and chart creation
    def create_heatmap_chart(df, category_col, score_cols, title, color_scheme): 
        if category_col not in df.columns or df[category_col].nunique() == 0 or df.empty:
            st.warning(f"Kolom '{category_col}' tidak ditemukan di data Survei atau tidak memiliki data unik.")
            return
            
        pivot_df = pd.pivot_table(df, values=score_cols, index=category_col, aggfunc='mean')
        
        # Reindex jika kolom kategori memiliki urutan spesifik
        if category_col == 'Pendidikan':
            pivot_df = pivot_df.reindex(pendidikan_order)
        elif category_col == 'Pendapatan':
            pivot_df = pivot_df.reindex(pendapatan_order)
        elif category_col == 'Pekerjaan':
            if len(pekerjaan_order) > 1 or pekerjaan_order[0] != 'N/A':
                 pivot_df = pivot_df.reindex(pekerjaan_order)

        # Ubah nama kolom agar lebih ringkas
        rename_map = {}
        for i, col in enumerate(score_cols):
            # Mempersingkat nama kolom pertanyaan (maksimal 30 karakter)
            rename_map[col] = f'P{i+1}: {col[:30].strip()}...' 
        
        pivot_df = pivot_df.rename(columns=rename_map)
        
        # Menentukan rentang warna yang konsisten (Min 1, Max 5)
        color_min = 1.0
        color_max = 5.0

        # Menggunakan Plotly untuk Heatmap
        fig = px.imshow(
            pivot_df.T, # Transpose agar pertanyaan di Y-Axis
            text_auto=".2f",
            aspect="auto",
            color_continuous_scale=color_scheme, # Menggunakan skema warna yang ditentukan
            labels=dict(x=category_col, y="Pertanyaan Detail", color="Rata-rata Skor"),
            title=title,
            template='plotly_white',
            zmin=color_min, # Batas bawah skor
            zmax=color_max  # Batas atas skor
        )
        
        # Penyesuaian Layout untuk X-axis dan Y-axis agar tidak tumpang tindih
        fig.update_xaxes(side="top", tickangle=-45)
        fig.update_yaxes(tickfont=dict(size=10)) # Mengurangi ukuran font untuk Y-axis
        
        fig.update_layout(
            height=450, # TINGGI SQUARISH
            margin=dict(t=100, b=40, l=220, r=20), # Margin kiri (l) ditambah untuk label Y-axis
            coloraxis_colorbar=dict(
                title="Rata-rata Skor",
                thicknessmode="pixels", thickness=20,
                lenmode="pixels", len=300, # Dikurangi agar proporsional
                yanchor="top", y=1,
                ticks="outside"
            ),
            font=dict(family='Poppins', size=12) # Menambahkan Poppins ke Plotly
        )
        st.plotly_chart(fig, use_container_width=True)

    # Helper function for Box Plot
    def create_boxplot_chart(df, x_col, y_col, title, x_order=None, color=COLOR_PRIMARY):
        if x_col not in df.columns or df[x_col].nunique() == 0 or df.empty:
            st.warning(f"Kolom '{x_col}' tidak ditemukan di data Survei atau tidak memiliki data unik.")
            return

        fig = px.box(
            df,
            x=x_col,
            y=y_col,
            category_orders={x_col: x_order} if x_order else None,
            title=title,
            color_discrete_sequence=[color],
            template='plotly_white'
        )
        fig.update_layout(yaxis_title=y_col, xaxis_title=x_col, font=dict(family='Poppins', size=12))
        st.plotly_chart(fig, use_container_width=True)

    # Helper function for Grouped Bar Chart / Single Bar Chart
    def create_bar_chart(df, x_col, y_col, color_col, title, color_map=None, x_order=None, single_color=COLOR_PRIMARY):
        if x_col not in df.columns or df[x_col].nunique() == 0 or df.empty:
            st.warning(f"Kolom '{x_col}' tidak ditemukan di data Survei atau tidak memiliki data unik.")
            return

        if color_col: # Grouped Bar
            df_grouped = df.groupby([x_col, color_col])[y_col].mean().reset_index()
            barmode='group'
            fig = px.bar(
                df_grouped,
                x=x_col,
                y=y_col,
                color=color_col,
                barmode=barmode,
                title=title,
                color_discrete_map=color_map if color_map else None,
                category_orders={x_col: x_order} if x_order else None,
                text_auto='.2f',
                template='plotly_white'
            )
        else: # Single Bar Chart
            df_grouped = df.groupby(x_col)[y_col].mean().reset_index()
            fig = px.bar(
                df_grouped,
                x=x_col,
                y=y_col,
                title=title,
                text_auto='.2f',
                color=x_col,
                color_discrete_sequence=[single_color],
                category_orders={x_col: x_order} if x_order else None,
                template='plotly_white'
            )

        fig.update_layout(yaxis_title=f"Rata-rata {y_col}", xaxis_title=x_col, font=dict(family='Poppins', size=12))
        st.plotly_chart(fig, use_container_width=True)

    
    if df_filtered.empty:
        st.error("Tidak ada data Survei yang tersedia untuk Provinsi yang dipilih.")
        return

    # --- A. INDEKS LITERASI KEUANGAN ---
    if selected_index == 'Indeks Literasi Keuangan':
        
        # 1. Heatmap PERTAMA (Pendidikan) - Full Width
        create_heatmap_chart(df_filtered, 'Pendidikan', literasi_cols, 
                             '1. Rata-Rata Skor Literasi Berdasarkan Pendidikan', 'YlGnBu')
        st.markdown("---")
        
        # 2. Heatmap KEDUA (Pekerjaan) - Full Width
        create_heatmap_chart(df_filtered, 'Pekerjaan', literasi_cols, 
                             '2. Rata-Rata Skor Literasi Berdasarkan Jenis Pekerjaan', 'YlGnBu')

        st.markdown("---")
        
        # 3. Boxplot vs Grouped Bar (Side-by-side)
        col_a3, col_a4 = st.columns(2)
        with col_a3:
            create_boxplot_chart(df_filtered, 'Pendapatan', 'Skor_Literasi', 
                                 '3. Dispersi Skor Literasi Keuangan Berdasarkan Kelompok Pendapatan', pendapatan_order, color=COLOR_LITERACY)
        
        with col_a4:
            # Bar chart Rata-Rata Skor Perilaku Keuangan Berdasarkan Status Tempat Tinggal (Single Bar)
            create_bar_chart(df_filtered, 'Status_Tinggal', 'Skor_Literasi', None, 
                             '4. Rata-Rata Skor Literasi Berdasarkan Status Tempat Tinggal', 
                             x_order=sorted(df_filtered['Status_Tinggal'].unique()), single_color=COLOR_LITERACY)

        # Grouped Bar Chart Rata-Rata Skor Literasi: Status Pernikahan vs Jenis Kelamin
        st.markdown("---")
        st.subheader("5. Rata-Rata Skor Literasi: Status Pernikahan vs Jenis Kelamin")
        create_bar_chart(df_filtered, 'Status_Nikah', 'Skor_Literasi', color_col='Gender', 
                             title='Grouped Bar: Rata-Rata Skor Literasi (Status Pernikahan vs. Gender)', 
                             color_map={'Pria': COLOR_PRIMARY, 'Wanita': COLOR_SECONDARY}, 
                             x_order=sorted(df_filtered['Status_Nikah'].unique()))


    # --- B. INDEKS PERILAKU KEUANGAN ---
    elif selected_index == 'Indeks Perilaku Keuangan':
        
        # 1. Heatmap PERILAKU PERTANYAAN vs. PENDAPATAN (Full width)
        create_heatmap_chart(df_filtered, 'Pendapatan', perilaku_cols, 
                             '1. HeatMap: Perilaku Pertanyaan vs Pendapatan', 'YlOrRd')
        
        st.markdown("---")
        
        # 2. Boxplot vs Bar Chart (Side-by-side)
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            # BOX PLOT: SKOR PERILAKU vs. PENDIDIKAN
            create_boxplot_chart(df_filtered, 'Pendidikan', 'Skor_Perilaku', 
                                 '2. Dispersi Skor Perilaku Keuangan vs. Pendidikan', pendidikan_order, color=COLOR_WARNING)
        with col_b2:
            # GROUPED BAR CHART: SKOR PERILAKU vs. STATUS TEMPAT TINGGAL (Single Bar)
            create_bar_chart(df_filtered, 'Status_Tinggal', 'Skor_Perilaku', None, 
                                     '3. Rata-Rata Skor Perilaku Berdasarkan Status Tempat Tinggal', 
                                     x_order=sorted(df_filtered['Status_Tinggal'].unique()), single_color=COLOR_WARNING)

    # --- C. INDEKS GAYA KEPUTUSAN & IMPULSIF ---
    elif selected_index == 'Indeks Gaya Keputusan & Impulsif':
        
        # 1. Heatmap (Pendidikan - Full width)
        create_heatmap_chart(df_filtered, 'Pendidikan', keputusan_cols, 
                             '1. Gaya Keputusan Pertanyaan vs Pendidikan', 'RdYlGn')
        
        st.markdown("---")
        
        # 2. Grouped Bar vs Boxplot (Side-by-side)
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            # GROUPED BAR CHART: SKOR KEPUTUSAN vs. JENIS KELAMIN (Single Bar)
            create_bar_chart(df_filtered, 'Gender', 'Skor_Keputusan', None, 
                                     '2. Rata-Rata Skor Keputusan Berdasarkan Jenis Kelamin', 
                                     single_color=COLOR_PRIMARY)
        with col_c2:
             # Boxplot (Pendapatan)
            create_boxplot_chart(df_filtered, 'Pendapatan', 'Skor_Keputusan', 
                             '3. Dispersi Skor Keputusan vs Pendapatan', pendapatan_order, color=COLOR_PRIMARY)
        
        st.markdown("---")
            
    # --- D. INDEKS KESEJAHTERAAN KEUANGAN ---
    elif selected_index == 'Indeks Kesejahteraan Keuangan':
        
        # 1. HEATMAP: KESEJAHTERAAN PERTANYAAN vs. PENDAPATAN (Full width)
        create_heatmap_chart(df_filtered, 'Pendapatan', kesejahteraan_cols, 
                             '1. Kesejahteraan Pertanyaan vs Pendapatan', 'PuBu')
        
        st.markdown("---")

        # 2. Boxplot vs Grouped Bar (Side-by-side)
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            # BOX PLOT: SKOR KESEJAHTERAAN vs. PENDIDIKAN
            create_boxplot_chart(df_filtered, 'Pendidikan', 'Skor_Kesejahteraan', 
                                 '2. Dispersi Skor Kesejahteraan vs Pendidikan', pendidikan_order, color=COLOR_SECONDARY)
        with col_d2:
            # GROUPED BAR CHART: SKOR KESEJAHTERAAN vs. PEKERJAAN (Single Bar)
            create_bar_chart(df_filtered, 'Pekerjaan', 'Skor_Kesejahteraan', None, 
                                     '3. Rata-Rata Skor Kesejahteraan Berdasarkan Jenis Pekerjaan', 
                                     x_order=pekerjaan_order, single_color=COLOR_SECONDARY)


# --- 7. LOGIKA UTAMA APLIKASI ---

# Sidebar Navigasi Utama
st.sidebar.title("Navigasi Dashboard")
selection = st.sidebar.radio(
    "Pilih Halaman Analisis", 
    ["Regional Analysis", "Profile Analysis", "Survey Analysis"]
)

# Injeksi CSS kustom (termasuk font Poppins)
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');

/* Menggunakan Poppins untuk seluruh body dan semua elemen text Streamlit */
html, body, [class*="st-"], h1, h2, h3, p, span, div {{
    font-family: 'Poppins', sans-serif !important;
}}

/* Menargetkan elemen input, label, dan sidebar text secara eksplisit */
.stApp, .stSidebar {{
    font-family: 'Poppins', sans-serif !important;
}}

/* Custom styling for Streamlit container */
.css-1d3z3vf {{
    padding-top: 2rem;
}}
h1, h2, h3 {{
    color: {COLOR_PRIMARY};
}}

/* Menambahkan padding horizontal pada elemen kolom (st.columns) */
/* Menargetkan wrapper kolom Streamlit */
.st-emotion-cache-18ni7ap {{ /* Ini adalah class yang membungkus konten kolom */
    padding-left: 10px; 
    padding-right: 10px; 
}}

/* Menambahkan margin bawah pada elemen markdown/header untuk spacing vertikal */
h2, h3 {{
    margin-bottom: 0.5rem;
}}

/* Memberi jarak pada setiap chart/elemen di dalam kolom */
[data-testid="column"] > div {{
    padding: 10px;
}}
</style>
""", unsafe_allow_html=True)


if selection == "Regional Analysis":
    page_regional(df_regional)
elif selection == "Profile Analysis":
    page_profile(df_profile)
elif selection == "Survey Analysis":
    page_survey(df_survey)
