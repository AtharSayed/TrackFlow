import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import base64
from pymongo import MongoClient
import pytz

# ===== MongoDB Setup =====
client = MongoClient('mongodb://localhost:27017')
db = client['crowdManagement']
users_collection = db['users']
reports_collection = db['reports']

# ===== BACKGROUND IMAGE HANDLER =====
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

bg_img_base64 = get_base64_image("E:/SideProject/crowdManagement/streamlit/background/backimg.jpg")

# ===== STREAMLIT CONFIG =====
st.set_page_config(page_title="Crowd Analytics Dashboard", layout="wide")

# ===== CUSTOM CSS =====
st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url("data:image/jpg;base64,{bg_img_base64}");
        background-size: cover;
        background-attachment: fixed;
        background-repeat: no-repeat;
        background-position: center;
    }}
    .block-container {{
        background-color: rgba(0, 0, 0, 0.7);
        padding: 2rem;
        border-radius: 16px;
        color: #f0f0f0;
    }}
    h1, h2, h3, h4, h5, h6 {{
        color: #ffffff !important;
        font-family: 'Segoe UI', sans-serif;
    }}
    .css-1d391kg {{
        color: #f0f0f0 !important;
    }}
    .sidebar .sidebar-content {{
        background-color: rgba(30, 30, 30, 0.9);
        color: #f0f0f0;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ===== TITLE =====
st.markdown("<h1 style='text-align: center;'>🚦 Crowd Analytics Dashboard</h1>", unsafe_allow_html=True)
st.markdown("---")

# ===== REFRESH INTERVAL =====
REFRESH_INTERVAL = 10  # seconds
st_autorefresh = st.empty()
st_autorefresh.markdown(
    f"<script>setTimeout(function() {{ window.location.reload(); }}, {REFRESH_INTERVAL*1000});</script>",
    unsafe_allow_html=True
)

# ===== SIDEBAR DATE FILTER =====
max_date = datetime.today()
min_date = max_date - timedelta(days=6)

st.sidebar.header("📅 Filter Options")
selected_date = st.sidebar.date_input(
    "Select Date",
    value=max_date.date(),
    min_value=min_date.date(),
    max_value=max_date.date()
)

# ===== TIMEZONE AWARE RANGE =====
timezone = pytz.timezone('Asia/Kolkata')
start_dt = timezone.localize(datetime.combine(selected_date, datetime.min.time()))
end_dt = start_dt + timedelta(days=1)

# ===== FETCH REPORTS FOR SELECTED DATE =====
reports_cursor = reports_collection.find({
    "report_time": {"$gte": start_dt, "$lt": end_dt}
})
reports_df = pd.DataFrame(list(reports_cursor))
if not reports_df.empty:
    reports_df["report_time"] = pd.to_datetime(reports_df["report_time"])

# ===== FETCH USERS FOR SELECTED DATE =====
users_cursor = users_collection.find({
    "registration_time": {"$gte": start_dt, "$lt": end_dt}
})
users_df = pd.DataFrame(list(users_cursor))
if not users_df.empty:
    users_df["registration_time"] = pd.to_datetime(users_df["registration_time"])

# ===== LIVE METRICS =====
st.subheader("📊 Live Metrics")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("👥 Total Entries Today", len(reports_df))

with col2:
    st.metric("🆔 Unique Users Today", len(users_df))

with col3:
    if len(reports_df) >= 50:
        st.error("⚠️ Overcrowding Detected!")
    else:
        st.success("✅ Safe Crowd Level")

# ===== HOURLY HEATMAP =====
st.subheader("🔥 Hourly Registration Heatmap")
if not users_df.empty:
    users_df["hour"] = users_df["registration_time"].dt.hour
    heatmap_data = users_df.groupby(["hour", "phone"]).size().reset_index(name="count")
    fig = px.density_heatmap(
        heatmap_data,
        x="hour",
        y="phone",
        z="count",
        color_continuous_scale="Plasma",
        title="Hourly Distribution of Registrations"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No user registration data available for selected date.")

# ===== DAILY TREND (7-DAY LOOKBACK) =====
st.subheader("📅 Daily Entry Trend (Past 7 Days)")
past_start = timezone.localize(datetime.combine(max_date - timedelta(days=6), datetime.min.time()))
past_end = timezone.localize(datetime.combine(max_date + timedelta(days=1), datetime.min.time()))

reports_7days_cursor = reports_collection.find({
    "report_time": {"$gte": past_start, "$lt": past_end}
})
reports_7days_df = pd.DataFrame(list(reports_7days_cursor))

if not reports_7days_df.empty:
    reports_7days_df["report_time"] = pd.to_datetime(reports_7days_df["report_time"])
    reports_7days_df["date"] = reports_7days_df["report_time"].dt.date
    daily_counts = reports_7days_df.groupby("date").size().reset_index(name="count")

    fig_line = px.line(
        daily_counts,
        x="date",
        y="count",
        markers=True,
        title="Entries Per Day",
        labels={"date": "Date", "count": "Entries"}
    )
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.warning("No data found for the past 7 days.")

# ===== PEAK HOURS BAR CHART =====
st.subheader("⏱️ Peak Hour Analysis")
if not reports_df.empty:
    reports_df["hour"] = reports_df["report_time"].dt.hour
    hour_counts = reports_df["hour"].value_counts().sort_index()
    fig_bar = px.bar(
        x=hour_counts.index,
        y=hour_counts.values,
        labels={"x": "Hour of Day", "y": "Entries"},
        title="Entries by Hour"
    )
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.warning("No hourly report data for selected date.")

# ===== TOP 5 FREQUENT VISITORS =====
st.subheader("🥇 Top 5 Frequent Visitors Today")
if not reports_df.empty:
    top_users = reports_df["person_phone"].value_counts().nlargest(5).reset_index()
    top_users.columns = ["Phone Number", "Entries"]
    fig_pie = px.pie(
        top_users,
        names="Phone Number",
        values="Entries",
        title="Top 5 Visitors"
    )
    st.plotly_chart(fig_pie, use_container_width=True)
else:
    st.warning("No frequent visitor data for selected date.")

# ===== RECENT ENTRIES =====
st.subheader("🧾 Recent Entries")
if not reports_df.empty:
    latest_entries = reports_df.sort_values(by="report_time", ascending=False).head(10)
    st.dataframe(latest_entries[["report_time", "person_id"]].rename(columns={
        "report_time": "Timestamp", "person_id": "Person ID"
    }))
else:
    st.warning("No entries found for today.")

# ===== FOOTER =====
st.markdown(
    "<div style='text-align: center; padding-top: 1rem; color: #ccc;'>"
    "Created by <b>Athar Sayed</b>, <b>Gaurav Sahu</b>, and <b>Rushikesh Kurhade</b>"
    "</div>",
    unsafe_allow_html=True
)
