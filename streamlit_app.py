import streamlit as st
import pandas as pd
import altair as alt
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="Hotel Bookings Dashboard", layout="wide")
session = get_active_session()
session.sql("USE DATABASE HOTEL_DB").collect()
session.sql("USE SCHEMA PUBLIC").collect() 


@st.cache_data(ttl=600)
def run(query: str) -> pd.DataFrame:
    return session.sql(query).to_pandas()


def bar(df, x, y, title, horizontal=False):
    """Bar chart sorted by value (largest first)."""
    enc_x = alt.X(f"{x}:N", sort="-y", title=None)
    enc_y = alt.Y(f"{y}:Q", title=None)
    if horizontal:
        enc_x, enc_y = alt.X(f"{y}:Q", title=None), alt.Y(f"{x}:N", sort="-x", title=None)
    chart = alt.Chart(df).mark_bar().encode(x=enc_x, y=enc_y, tooltip=[x, y])
    st.subheader(title)
    st.altair_chart(chart, use_container_width=True)


st.title("Hotel Bookings Dashboard")

# ---------------- KPIs ----------------
kpi = run("""
    SELECT
        AVG(total_amount)  AS avg_booking_value,
        SUM(num_guests)    AS total_guests,
        COUNT(*)           AS total_bookings,
        SUM(total_amount)  AS total_revenue
    FROM GOLD_BOOKING_CLEAN
""").iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Avg Booking Value", f"{kpi['AVG_BOOKING_VALUE']:,.2f}")
c2.metric("Total Guests", f"{int(kpi['TOTAL_GUESTS']):,}")
c3.metric("Total Bookings", f"{int(kpi['TOTAL_BOOKINGS']):,}")
c4.metric("Total Revenue", f"{kpi['TOTAL_REVENUE']:,.2f}")

st.divider()

# ---------------- Line charts ----------------
daily = run("""
    SELECT date, total_revenue, total_booking
    FROM GOLD_AGG_DAILY_BOOKING
    ORDER BY date
""")
daily["DATE"] = pd.to_datetime(daily["DATE"])

grain = st.radio("Time grain", ["Monthly", "Daily"], horizontal=True)
if grain == "Monthly":
    ts = daily.set_index("DATE").resample("MS").sum(numeric_only=True)
else:
    ts = daily.set_index("DATE")

l, r = st.columns(2)
with l:
    st.subheader(f"{grain} Revenue")
    st.line_chart(ts["TOTAL_REVENUE"])
with r:
    st.subheader(f"{grain} Bookings")
    st.line_chart(ts["TOTAL_BOOKING"])

st.divider()

# ---------------- Bar charts ----------------
top_cities = run("""
    SELECT hotel_city, total_revenue
    FROM GOLD_AGG_HOTEL_CITY_SALES
    WHERE total_revenue IS NOT NULL
    ORDER BY total_revenue DESC
    LIMIT 5
""")
by_status = run("""
    SELECT booking_status, COUNT(*) AS total
    FROM GOLD_BOOKING_CLEAN
    GROUP BY booking_status
""")
by_type = run("""
    SELECT room_type, COUNT(*) AS total_bookings
    FROM GOLD_BOOKING_CLEAN
    GROUP BY room_type
    ORDER BY total_bookings DESC
""")

a, b = st.columns(2)
with a:
    bar(top_cities, "HOTEL_CITY", "TOTAL_REVENUE", "Top 5 Cities by Revenue")
with b:
    bar(by_status, "BOOKING_STATUS", "TOTAL", "Bookings by Status")

bar(by_type, "ROOM_TYPE", "TOTAL_BOOKINGS", "Bookings by Room Type")
