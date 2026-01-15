import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
import os
from babel.numbers import format_currency

# Set Page Configuration
st.set_page_config(page_title="E-Commerce Dashboard", layout="wide")
sns.set(style='dark')

# --- FUNGSI LOAD DATA (DENGAN CACHE) ---
# Fungsi ini akan menggabungkan data secara otomatis saat dashboard dibuka
@st.cache_data
def load_data():
    # Mengambil path folder tempat script ini berada
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Membaca dataset mentah (pastikan file-file ini ada di folder dashboard di GitHub)
    orders_df = pd.read_csv(os.path.join(current_dir, "orders_dataset.csv"))
    items_df = pd.read_csv(os.path.join(current_dir, "order_items_dataset.csv"))
    products_df = pd.read_csv(os.path.join(current_dir, "products_dataset.csv"))
    customers_df = pd.read_csv(os.path.join(current_dir, "customers_dataset.csv"))

    # Merging Data secara instan
    # Kita hanya mengambil kolom yang perlu agar hemat memori
    main_df = pd.merge(orders_df, items_df, on="order_id")
    main_df = pd.merge(main_df, customers_df, on="customer_id")
    main_df = pd.merge(main_df, products_df[["product_id", "product_category_name"]], on="product_id")
    
    # Konversi tanggal
    datetime_columns = ["order_purchase_timestamp", "order_delivered_customer_date"]
    for column in datetime_columns:
        main_df[column] = pd.to_datetime(main_df[column])
        
    main_df.sort_values(by="order_purchase_timestamp", inplace=True)
    return main_df

# Load Data
all_df = load_data()

# --- HELPER FUNCTIONS ---
def create_daily_orders_df(df):
    daily_orders_df = df.resample(rule='D', on='order_purchase_timestamp').agg({
        "order_id": "nunique",
        "price": "sum"
    }).reset_index()
    daily_orders_df.rename(columns={"order_id": "order_count", "price": "revenue"}, inplace=True)
    return daily_orders_df

def create_sum_order_items_df(df):
    return df.groupby("product_category_name").order_id.nunique().sort_values(ascending=False).reset_index()

def create_by_state_df(df):
    return df.groupby(by="customer_state").customer_unique_id.nunique().reset_index().rename(columns={"customer_unique_id": "customer_count"})

def create_rfm_df(df):
    rfm_df = df.groupby(by="customer_unique_id", as_index=False).agg({
        "order_purchase_timestamp": "max",
        "order_id": "nunique",
        "price": "sum"
    })
    rfm_df.columns = ["customer_id", "max_order_timestamp", "frequency", "monetary"]
    rfm_df["max_order_timestamp"] = rfm_df["max_order_timestamp"].dt.date
    recent_date = df["order_purchase_timestamp"].dt.date.max()
    rfm_df["recency"] = rfm_df["max_order_timestamp"].apply(lambda x: (recent_date - x).days)
    rfm_df.drop("max_order_timestamp", axis=1, inplace=True)
    return rfm_df

# --- FILTER TANGGAL (HALAMAN UTAMA) ---
st.header('Dicoding Collection Dashboard :sparkles:')

min_date = all_df["order_purchase_timestamp"].min().date()
max_date = all_df["order_purchase_timestamp"].max().date()

# Meletakkan filter tanggal di halaman utama (seperti permintaan sebelumnya)
col_date1, _ = st.columns([1, 2])
with col_date1:
    date_range = st.date_input(
        label='Rentang Waktu Analisis',
        min_value=min_date,
        max_value=max_date,
        value=[min_date, max_date]
    )

# Filter logic
if isinstance(date_range, list) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range[0] if isinstance(date_range, list) else date_range

main_df = all_df[(all_df["order_purchase_timestamp"].dt.date >= start_date) & 
                (all_df["order_purchase_timestamp"].dt.date <= end_date)]

# Siapkan Dataframe
daily_orders_df = create_daily_orders_df(main_df)
sum_order_items_df = create_sum_order_items_df(main_df)
bystate_df = create_by_state_df(main_df)
rfm_df = create_rfm_df(main_df)

# --- VISUALISASI ---
st.subheader('Pesanan Harian (Daily Orders)')
col1, col2 = st.columns(2)
with col1:
    st.metric("Total Pesanan", value=daily_orders_df.order_count.sum())
with col2:
    st.metric("Total Pendapatan", value=format_currency(daily_orders_df.revenue.sum(), "BRL", locale='pt_BR'))

fig, ax = plt.subplots(figsize=(16, 6))
ax.plot(daily_orders_df["order_purchase_timestamp"], daily_orders_df["order_count"], marker='o', linewidth=2, color="#90CAF9")
st.pyplot(fig)

st.subheader("Performa Penjualan Produk")
fig, ax = plt.subplots(nrows=1, ncols=2, figsize=(24, 6))
sns.barplot(x="order_id", y="product_category_name", data=sum_order_items_df.head(5), palette="Blues_r", ax=ax[0])
ax[0].set_title("Produk Paling Laris", fontsize=15)
sns.barplot(x="order_id", y="product_category_name", data=sum_order_items_df.sort_values(by="order_id", ascending=True).head(5), palette="Reds_r", ax=ax[1])
ax[1].set_title("Produk Paling Sedikit Terjual", fontsize=15)
ax[1].invert_xaxis()
ax[1].yaxis.tick_right()
st.pyplot(fig)

st.subheader("Demografi & Pelanggan Terbaik")
col_d1, col_d2 = st.columns(2)
with col_d1:
    fig, ax = plt.subplots(figsize=(12, 8))
    sns.barplot(x="customer_count", y="customer_state", data=bystate_df.sort_values(by="customer_count", ascending=False).head(10), palette="viridis")
    ax.set_title("Pelanggan Berdasarkan Negara Bagian", fontsize=15)
    st.pyplot(fig)
with col_d2:
    fig, ax = plt.subplots(figsize=(12, 8))
    sns.barplot(y="monetary", x="customer_id", data=rfm_df.sort_values(by="monetary", ascending=False).head(5), palette="rocket")
    ax.set_title("Top 5 Pelanggan (Monetary)", fontsize=15)
    plt.xticks(rotation=45)
    st.pyplot(fig)

st.caption('Dibuat oleh Kendrick Filbert | Proyek Akhir Dicoding 2025')
