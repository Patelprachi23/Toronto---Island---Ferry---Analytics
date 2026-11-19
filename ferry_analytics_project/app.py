import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Toronto Island Ferry Analytics", page_icon="⛴️", layout="wide")
ROOT = Path(__file__).parent
DATA = ROOT / "data" / "ferry_cleaned_featured.csv"

@st.cache_data
def load_data():
    d = pd.read_csv(DATA, parse_dates=["Timestamp"])
    d = d.sort_values("Timestamp")
    d["DateOnly"] = d["Timestamp"].dt.date
    return d

df = load_data()
st.title("⛴️ Toronto Island Ferry Ticket Sales & Redemption Analytics")
st.caption("Historical analytics dashboard | Latest available data snapshot — not a live ticketing feed")
latest = df["Timestamp"].max()
st.sidebar.header("Filters")
dmin, dmax = df["Timestamp"].min().date(), df["Timestamp"].max().date()
dates = st.sidebar.date_input("Date range", value=(dmin, dmax), min_value=dmin, max_value=dmax)
if isinstance(dates, tuple) and len(dates)==2:
    start, end = dates
else:
    start, end = dmin, dmax
hours = st.sidebar.slider("Hour of day", 0, 23, (0, 23))
day_types = st.sidebar.multiselect("Day type", ["Weekday","Weekend"], default=["Weekday","Weekend"])
seasons = st.sidebar.multiselect("Season", ["Winter","Spring","Summer","Fall"], default=["Winter","Spring","Summer","Fall"])
f = df[(df["Timestamp"].dt.date>=start)&(df["Timestamp"].dt.date<=end)&
       (df["Hour"].between(hours[0],hours[1]))&df["Day Type"].isin(day_types)&df["Season"].isin(seasons)]
if f.empty:
    st.warning("No records match the selected filters.")
    st.stop()

sales, red = int(f["Sales Count"].sum()), int(f["Redemption Count"].sum())
net = sales-red
c1,c2,c3,c4 = st.columns(4)
c1.metric("Tickets sold", f"{sales:,}")
c2.metric("Tickets redeemed", f"{red:,}")
c3.metric("Net movement (sales − redemptions)", f"{net:,}")
c4.metric("Records in selection", f"{len(f):,}")
st.caption(f"Dataset latest timestamp: {latest:%d %b %Y, %H:%M} | Selected interval: {start} to {end}")

st.subheader("Ticket activity over time")
freq = st.radio("Aggregation", ["15-minute/source records","Hourly","Daily"], horizontal=True)
if freq=="Hourly":
    chart = f.set_index("Timestamp").resample("h").agg({"Sales Count":"sum","Redemption Count":"sum","Net Movement":"sum"}).reset_index()
elif freq=="Daily":
    chart = f.set_index("Timestamp").resample("D").agg({"Sales Count":"sum","Redemption Count":"sum","Net Movement":"sum"}).reset_index()
else:
    chart = f[["Timestamp","Sales Count","Redemption Count"]].copy()
long = chart.melt(id_vars="Timestamp", value_vars=["Sales Count","Redemption Count"], var_name="Measure", value_name="Tickets")
st.plotly_chart(px.line(long, x="Timestamp", y="Tickets", color="Measure", title="Sales vs redemptions"), use_container_width=True)

left,right=st.columns(2)
with left:
    st.subheader("Average activity by hour")
    h = f.groupby("Hour",as_index=False)[["Sales Count","Redemption Count"]].mean()
    hlong=h.melt(id_vars="Hour",var_name="Measure",value_name="Average count")
    st.plotly_chart(px.bar(hlong,x="Hour",y="Average count",color="Measure",barmode="group"),use_container_width=True)
with right:
    st.subheader("Seasonal comparison")
    s=f.groupby("Season",as_index=False)[["Sales Count","Redemption Count"]].mean()
    slong=s.melt(id_vars="Season",var_name="Measure",value_name="Average count")
    st.plotly_chart(px.bar(slong,x="Season",y="Average count",color="Measure",barmode="group",category_orders={"Season":["Winter","Spring","Summer","Fall"]}),use_container_width=True)

st.subheader("Peak vs off-peak")
h=f.groupby("Hour",as_index=False)["Sales Count"].mean()
threshold=h["Sales Count"].quantile(.75)
h["Demand band"]=h["Sales Count"].apply(lambda x:"Peak (top quartile)" if x>=threshold else "Other")
st.write(f"Peak-hour threshold (75th percentile of mean interval sales): **{threshold:.2f} tickets per recorded interval**.")
st.plotly_chart(px.bar(h,x="Hour",y="Sales Count",color="Demand band",title="Mean sales per recorded interval by hour"),use_container_width=True)

st.subheader("Daily and weekday patterns")
d=f.groupby("Day of Week",as_index=False)[["Sales Count","Redemption Count"]].mean()
order=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
d["Day of Week"]=pd.Categorical(d["Day of Week"],categories=order,ordered=True)
d=d.sort_values("Day of Week")
st.plotly_chart(px.bar(d,x="Day of Week",y=["Sales Count","Redemption Count"],barmode="group"),use_container_width=True)

st.subheader("Rolling averages")
roll=f.sort_values("Timestamp").set_index("Timestamp")
roll["Sales 1H"] = roll["Sales Count"].rolling("1h",min_periods=1).mean()
roll["Sales 4H"] = roll["Sales Count"].rolling("4h",min_periods=1).mean()
r=roll[["Sales 1H","Sales 4H"]].reset_index().melt(id_vars="Timestamp",var_name="Window",value_name="Average sales")
st.plotly_chart(px.line(r,x="Timestamp",y="Average sales",color="Window"),use_container_width=True)

with st.expander("Data quality and definitions"):
    st.markdown("""
    - **Net movement:** ticket sales minus ticket redemptions for the selected records.
    - **Peak hours:** hours whose average sales per source record are at or above the 75th percentile in the selected data.
    - **Season:** Winter (Dec–Feb), Spring (Mar–May), Summer (Jun–Aug), Fall (Sep–Nov).
    - **Off-Season Utilization Index:** lowest seasonal mean sales divided by highest seasonal mean sales × 100; relative index, not ferry-capacity utilization.
    - Counts represent ticket activity, not a verified count of people physically aboard.
    - The source file is static. No live API or automatic refresh is connected.
    """)
st.download_button("Download filtered records", f.to_csv(index=False).encode("utf-8"), "filtered_ferry_activity.csv", "text/csv")
