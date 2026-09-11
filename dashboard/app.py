"""Streamlit dashboard for the prepared European bike-sharing aggregates."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import CITY_COLORS, PROCESSED_DIR  # noqa: E402


st.set_page_config(page_title="European Bike Sharing Analytics", layout="wide")


@st.cache_data
def load_table(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path.name}. Run python scripts/prepare_data.py and "
            "python scripts/run_analysis.py."
        )
    return pd.read_parquet(path)


def format_number(value: float, digits: int = 0) -> str:
    if pd.isna(value):
        return "n.a."
    return f"{value:,.{digits}f}"


kpis = load_table("city_kpis")
hourly = load_table("hourly_demand")
weekday = load_table("weekday_weekend")
stations = load_table("station_performance")
characteristics = load_table("trip_characteristics")
fleet = load_table("bike_utilization")
bike_types = load_table("bike_type_analysis")

st.title("European Bike Sharing Analytics")
st.caption(
    "Observed demand, trip behavior, station activity, and fleet utilization. "
    "Comparisons use local time and normalized rates where observation coverage differs."
)

city = st.sidebar.selectbox("City", sorted(kpis["city"].tolist()))
day_filter = st.sidebar.radio("Day type", ["All days", "Weekday", "Weekend"])
row = kpis.loc[kpis["city"] == city].iloc[0]

metric_columns = st.columns(6)
metric_columns[0].metric("Trips", format_number(row["total_trips"]))
metric_columns[1].metric("Trips / active day", format_number(row["trips_per_active_day"]))
metric_columns[2].metric("Median duration", f"{row['median_duration_min']:.1f} min")
metric_columns[3].metric("Median distance", f"{row['median_distance_km']:.2f} km")
metric_columns[4].metric("Stations", format_number(row["stations"]))
metric_columns[5].metric("Fleet utilization proxy", format_number(row["fleet_utilization_proxy"], 2))

left, right = st.columns(2)
with left:
    city_hourly = hourly.loc[hourly["city"] == city]
    fig = px.line(
        city_hourly,
        x="hour",
        y="trip_share",
        markers=True,
        title=f"Hourly Demand in {city}",
        labels={"hour": "Local hour", "trip_share": "Share of trips"},
        color_discrete_sequence=[CITY_COLORS.get(city, "#2563EB")],
    )
    fig.update_yaxes(tickformat=".1%")
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with right:
    city_weekday = weekday.loc[weekday["city"] == city].sort_values("day_of_week")
    if day_filter != "All days":
        city_weekday = city_weekday.loc[city_weekday["day_type"] == day_filter]
    fig = px.bar(
        city_weekday,
        x="day_name",
        y="trips_per_active_day",
        color="day_type",
        title=f"Demand by Day of Week in {city}",
        labels={"day_name": "Day", "trips_per_active_day": "Trips per observed day"},
        color_discrete_map={"Weekday": "#475569", "Weekend": "#94A3B8"},
    )
    fig.update_layout(legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)
with left:
    top = stations.loc[stations["city"] == city].sort_values("total_activity").tail(10)
    if top.empty:
        st.info("Station analysis is unavailable because station IDs are not observed.")
    else:
        fig = px.bar(
            top,
            x="total_activity",
            y="station_name",
            orientation="h",
            title=f"Most Active Stations in {city}",
            labels={"total_activity": "Starts + ends", "station_name": "Station"},
            color_discrete_sequence=[CITY_COLORS.get(city, "#2563EB")],
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

with right:
    city_types = bike_types.loc[bike_types["city"] == city]
    fig = px.bar(
        city_types,
        x="propulsion_type",
        y="trip_share",
        title=f"Trips by Propulsion Type in {city}",
        labels={"propulsion_type": "Propulsion type", "trip_share": "Share of trips"},
        color="propulsion_type",
        color_discrete_map={
            "electric_assist": "#38BDF8", "human": "#334155", "unknown": "#CBD5E1"
        },
    )
    fig.update_yaxes(tickformat=".0%")
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Cross-city comparison")
left, right = st.columns(2)
with left:
    comparison = characteristics.melt(
        id_vars="city",
        value_vars=["median_duration_min", "median_distance_km"],
        var_name="metric",
        value_name="value",
    )
    comparison["metric"] = comparison["metric"].map(
        {"median_duration_min": "Duration (min)", "median_distance_km": "Distance (km)"}
    )
    fig = px.bar(
        comparison,
        x="city",
        y="value",
        facet_col="metric",
        facet_col_wrap=2,
        color="city",
        title="Median Trip Characteristics",
        color_discrete_map=CITY_COLORS,
    )
    fig.update_yaxes(matches=None)
    fig.update_layout(showlegend=False)
    fig.for_each_annotation(lambda annotation: annotation.update(text=annotation.text.split("=")[-1]))
    st.plotly_chart(fig, use_container_width=True)

with right:
    comparison = kpis.merge(
        fleet[["city", "fleet_utilization_proxy"]],
        on="city",
        suffixes=("", "_fleet"),
    )
    fig = px.scatter(
        comparison,
        x="trips_per_active_day",
        y="fleet_utilization_proxy",
        size="total_trips",
        color="city",
        text="city",
        title="Demand vs Fleet Utilization Proxy",
        labels={
            "trips_per_active_day": "Trips per active day",
            "fleet_utilization_proxy": "Trips per observed bike per active day",
        },
        color_discrete_map=CITY_COLORS,
    )
    fig.update_traces(textposition="top center")
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Fleet utilization is a proxy based on bikes observed in trips, not a verified fleet-capacity measure. "
    "Station rankings are limited to trips with station IDs."
)

