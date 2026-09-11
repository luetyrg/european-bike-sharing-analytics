"""Reusable static chart functions for the report and README."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.config import CITY_COLORS


def _style_axis(ax: plt.Axes, title: str, xlabel: str = "", ylabel: str = "") -> None:
    ax.set_title(title, loc="left", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.2)


def _save(fig: plt.Figure, output_dir: Path, name: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / name
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def create_all_figures(results: dict[str, pd.DataFrame], output_dir: Path) -> list[Path]:
    """Create eight compact, interview-friendly static figures."""

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    paths: list[Path] = []
    kpis = results["city_kpis"].sort_values("trips_per_active_day")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(
        kpis["city"],
        kpis["trips_per_active_day"],
        color=[CITY_COLORS.get(city, "#64748B") for city in kpis["city"]],
    )
    _style_axis(ax, "Trips per Active Day", "Trips per active day")
    paths.append(_save(fig, output_dir, "trips_per_active_day.png"))

    hourly = results["hourly_demand"]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for city, group in hourly.groupby("city"):
        ax.plot(
            group["hour"], group["trip_share"] * 100,
            marker="o", markersize=2.5, linewidth=2,
            label=city, color=CITY_COLORS.get(city),
        )
    _style_axis(ax, "Hourly Demand Profile", "Local hour", "Share of city trips (%)")
    ax.set_xticks(range(0, 24, 2))
    ax.legend(frameon=False, ncol=4, loc="upper center")
    paths.append(_save(fig, output_dir, "hourly_demand_profile.png"))

    day_type = results["weekday_weekend"].copy()
    pivot = day_type.pivot(index="city", columns="day_type", values="trips_per_active_day")
    pivot = pivot.reindex(kpis["city"])
    fig, ax = plt.subplots(figsize=(8, 5.0))
    pivot.plot(kind="barh", ax=ax, color=["#475569", "#94A3B8"])
    _style_axis(ax, "Weekday and Weekend Demand", "Trips per observed day")
    ax.legend(title="", frameon=False)
    paths.append(_save(fig, output_dir, "weekday_weekend_demand.png"))

    characteristics = results["trip_characteristics"].set_index("city").reindex(kpis["city"])
    for column, title, xlabel, filename in (
        ("median_duration_min", "Median Trip Duration", "Minutes", "median_duration.png"),
        ("median_distance_km", "Median Trip Distance", "Kilometres", "median_distance.png"),
    ):
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.barh(
            characteristics.index,
            characteristics[column],
            color=[CITY_COLORS.get(city, "#64748B") for city in characteristics.index],
        )
        _style_axis(ax, title, xlabel)
        paths.append(_save(fig, output_dir, filename))

    stations = results["station_performance"]
    cities = list(kpis.sort_values("city")["city"])
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.5))
    for ax, city in zip(axes.flat, cities):
        group = stations.loc[stations["city"] == city].sort_values("total_activity").tail(7)
        if group.empty:
            ax.text(0.5, 0.5, "No station-linked trips", ha="center", va="center")
            ax.set_axis_off()
            ax.set_title(city, loc="left", fontweight="bold")
            continue
        labels = group["station_name"].str.slice(0, 34)
        ax.barh(labels, group["total_activity"], color=CITY_COLORS.get(city))
        _style_axis(ax, city, "Starts + ends")
        ax.tick_params(axis="y", labelsize=8)
    fig.suptitle("Most Active Stations", x=0.06, ha="left", fontsize=15, fontweight="bold")
    fig.tight_layout()
    paths.append(_save(fig, output_dir, "top_stations.png"))

    fleet = results["bike_utilization"].sort_values("fleet_utilization_proxy")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(
        fleet["city"], fleet["fleet_utilization_proxy"],
        color=[CITY_COLORS.get(city, "#64748B") for city in fleet["city"]],
    )
    _style_axis(
        ax,
        "Fleet Utilization Proxy",
        "Trips per observed bike per active day",
    )
    paths.append(_save(fig, output_dir, "fleet_utilization_proxy.png"))

    bike_types = results["bike_type_analysis"].copy()
    type_pivot = bike_types.pivot_table(
        index="city", columns="propulsion_type", values="trip_share", fill_value=0
    ).reindex(kpis["city"])
    fig, ax = plt.subplots(figsize=(8, 4.6))
    type_colors = {
        "electric_assist": "#38BDF8",
        "human": "#334155",
        "unknown": "#CBD5E1",
    }
    type_pivot.plot(
        kind="barh",
        stacked=True,
        ax=ax,
        color=[type_colors.get(column, "#A78BFA") for column in type_pivot.columns],
    )
    _style_axis(ax, "Trips by Propulsion Type", "Share of all city trips")
    ax.xaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    ax.legend(title="", frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)
    paths.append(_save(fig, output_dir, "bike_type_share.png"))

    return paths
