# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Zomato Delivery Dashboard",
                   layout="wide",
                   page_icon="🍔")

# ---------- Helpers ----------
@st.cache_data
def load_data(path: str):
    df = pd.read_excel(path)
    # Normalisasi kolom penting (antisipasi variasi nama)
    # pastikan kolom berikut ada di file:
    # Order_Date, City, Rating_Group, Delivery_person_Ratings, Time_taken (min),
    # order_hour, Festival, Weather_conditions, Road_traffic_density
    # Konversi tanggal
    if np.issubdtype(df["Order_Date"].dtype, np.number):
        # serial excel → date
        df["Order_Date"] = pd.to_datetime("1899-12-30") + pd.to_timedelta(df["Order_Date"], unit="D")
    else:
        df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce", dayfirst=True)
    # Jam (fallback)
    if "order_hour" not in df.columns:
        # kalau ada Time_Orderd, ambil jamnya
        if "Time_Orderd" in df.columns:
            dt = pd.to_datetime(df["Time_Orderd"], errors="coerce")
            df["order_hour"] = dt.dt.hour
        else:
            df["order_hour"] = df["Order_Date"].dt.hour.fillna(0).astype(int)
    # Rating group (bulatkan 1–5 kalau perlu)
    if "Rating_Group" not in df.columns and "Delivery_person_Ratings" in df.columns:
        df["Rating_Group"] = df["Delivery_person_Ratings"].round().clip(1, 5).astype(int)
    # Festival normalize to Yes/No
    if "Festival" in df.columns:
        df["Festival"] = df["Festival"].astype(str).str.strip().str.title().replace({"True":"Yes","False":"No"})
    return df

df = load_data("data/cleaned_dataset.xlsx")

# ---------- Header ----------
st.markdown(
    "<h2 style='text-align:center;margin-bottom:8px'>📊 Analisis Operasional & Kepuasan Pelanggan pada Layanan Zomato Delivery</h2>",
    unsafe_allow_html=True
)

# ---------- Filters bar (3 kolom) ----------
f1, f2, f3 = st.columns([1.1, 1, 1])
with f1:
    date_range = st.date_input(
        "Filter Order Date",
        value=(df["Order_Date"].min().date(), df["Order_Date"].max().date())
    )
with f2:
    sel_city = st.multiselect(
        "Filter City",
        options=sorted(df["City"].dropna().unique().tolist()),
        default=sorted(df["City"].dropna().unique().tolist())
    )
with f3:
    sel_rating = st.multiselect(
        "Filter Rating Group",
        options=sorted(df["Rating_Group"].dropna().unique().tolist()),
        default=sorted(df["Rating_Group"].dropna().unique().tolist())
    )

# Terapkan filter
if isinstance(date_range, tuple):
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
else:
    start_date, end_date = df["Order_Date"].min(), df["Order_Date"].max()

mask = (
    (df["Order_Date"].between(start_date, end_date)) &
    (df["City"].isin(sel_city)) &
    (df["Rating_Group"].isin(sel_rating))
)
dff = df.loc[mask].copy()

# ---------- KPI cards ----------
k1, k2, k3 = st.columns(3)
k1.metric("📦 Count of Orders", f"{len(dff):,.0f}")
k2.metric("⏱ Avg Time Taken (min)", f"{dff['Time_taken (min)'].mean():.2f}")
k3.metric("⭐ Avg Rating", f"{dff['Delivery_person_Ratings'].mean():.2f}")

st.markdown("---")
st.subheader("🔧 Operasional")

# ---------- Row 1: Line & Table (opsional ganti table) ----------
c1, c2 = st.columns((1.6, 1))
with c1:
    by_day = dff.groupby("Order_Date").size().reset_index(name="Orders").sort_values("Order_Date")
    fig1 = px.area(by_day, x="Order_Date", y="Orders",
                   title="Count of Orders by Date")
    fig1.update_traces(line_color="#1f77b4")
    st.plotly_chart(fig1, use_container_width=True)
with c2:
    by_city = dff.groupby("City")["Time_taken (min)"].mean().reset_index()
    fig2 = px.bar(by_city, x="City", y="Time_taken (min)",
                  title="Avg Time Taken by City",
                  text_auto=".1f")
    st.plotly_chart(fig2, use_container_width=True)

# ---------- Row 2: order_hour × Festival (clustered column) & Order Period count ----------
c3, c4 = st.columns(2)
with c3:
    tmp = dff.groupby(["order_hour", "Festival"]).size().reset_index(name="Orders")
    fig3 = px.bar(tmp, x="order_hour", y="Orders", color="Festival",
                  barmode="group", title="Count of Orders by Hour & Festival")
    fig3.update_layout(xaxis_title="Hour (0–23)")
    st.plotly_chart(fig3, use_container_width=True)

with c4:
    # Buat order period jika belum ada
    if "order_period" not in dff.columns:
        def order_period(x):
            if 4 <= x < 11:  # 04–10
                return "Morning"
            elif 11 <= x < 14:
                return "Afternoon"
            elif 14 <= x < 18:
                return "Evening"
            else:
                return "Night"
        dff["order_period"] = dff["order_hour"].fillna(0).astype(int).map(order_period)
    tmp2 = dff.groupby(["order_period"]).size().reset_index(name="Orders")
    order_map = {"Morning":0, "Afternoon":1, "Evening":2, "Night":3}
    tmp2["sort"] = tmp2["order_period"].map(order_map)
    tmp2 = tmp2.sort_values("sort")
    fig4 = px.bar(tmp2, x="order_period", y="Orders",
                  title="Count by Order Period")
    st.plotly_chart(fig4, use_container_width=True)

st.subheader("😊 Kepuasan Pelanggan")

# ---------- Row 3: Speed vs Rating & Weather vs Rating ----------
c5, c6 = st.columns(2)
with c5:
    if "delivery_speed" in dff.columns:
        speed_avg = dff.groupby("delivery_speed")["Delivery_person_Ratings"].mean().reset_index()
        fig5 = px.bar(speed_avg, x="delivery_speed", y="Delivery_person_Ratings",
                      title="Delivery Speed vs Rating", text_auto=".2f")
        st.plotly_chart(fig5, use_container_width=True)
    else:
        st.info("Kolom 'delivery_speed' tidak ditemukan di dataset.")

with c6:
    w_avg = dff.groupby("Weather_conditions")["Delivery_person_Ratings"].mean().reset_index()
    fig6 = px.bar(w_avg, x="Weather_conditions", y="Delivery_person_Ratings",
                  title="Weather vs Rating", text_auto=".2f")
    st.plotly_chart(fig6, use_container_width=True)

# ---------- Row 4: Traffic vs Rating & Rating Group gauge-ish (donut) ----------
c7, c8 = st.columns(2)
with c7:
    t_avg = dff.groupby("Road_traffic_density")["Delivery_person_Ratings"].mean().reset_index()
    fig7 = px.bar(t_avg, x="Road_traffic_density", y="Delivery_person_Ratings",
                  title="Road Traffic vs Rating", text_auto=".2f")
    st.plotly_chart(fig7, use_container_width=True)

with c8:
    rg = dff["Rating_Group"].value_counts().sort_index().reset_index()
    rg.columns = ["Rating", "Count"]
    fig8 = px.pie(rg, names="Rating", values="Count",
                  title="Rating Group Distribution", hole=0.6)
    st.plotly_chart(fig8, use_container_width=True)

st.caption("Dashboard built with Streamlit & Plotly")
