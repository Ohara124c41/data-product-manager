#!/usr/bin/env python3
"""Reproducible analysis for the Flyber MVP launch strategy project.

The program analyzes the full taxi CSV and survey CSV, applies documented
operational-quality filters, spatially joins endpoints to official NYC 2020
Neighborhood Tabulation Areas (NTAs), and emits tables, charts, a JSON summary,
and an optional Tableau-ready enriched CSV.

The 2020 NTA boundary file is used as an official third-party geographic
overlay. Because the ride data are from 2016, this is an approximation and is
explicitly recorded in the outputs.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.request import urlopen

os.environ.setdefault("MPLCONFIGDIR", "/tmp/flyber-matplotlib")

import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.path import Path as MplPath
import numpy as np
import pandas as pd


NTA_URL = "https://data.cityofnewyork.us/resource/9nt8-h7nd.geojson?$limit=500"
DECK_COLORS = {
    "coral": "#ff836f",
    "gold": "#f9cd5d",
    "teal": "#159ba4",
    "teal_light": "#42a5aa",
    "ink": "#243746",
    "muted": "#6b7785",
    "paper": "#f7f7f5",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--taxi", required=True, help="Path to taxi_rides.csv")
    parser.add_argument("--survey", required=True, help="Path to user-research.csv")
    parser.add_argument("--output-dir", required=True, help="Directory for outputs")
    parser.add_argument(
        "--nta-geojson",
        default=None,
        help="Optional cached NTA GeoJSON. Downloaded from NYC Open Data if omitted.",
    )
    parser.add_argument(
        "--write-tableau",
        action="store_true",
        help="Write a full Tableau-ready taxi extract with derived and NTA fields.",
    )
    return parser.parse_args()


def ensure_nta(path: Path | None, output_dir: Path) -> Path:
    target = path or output_dir / "nyc_nta_2020.geojson"
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(NTA_URL, timeout=60) as response:
        target.write_bytes(response.read())
    return target


def polygon_parts(geometry: dict) -> list[list[list[list[float]]]]:
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    if geometry["type"] == "MultiPolygon":
        return geometry["coordinates"]
    return []


def assign_nta(
    longitude: np.ndarray,
    latitude: np.ndarray,
    features: list[dict],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Assign points to NTAs using vectorized polygon containment tests."""
    points = np.column_stack([longitude, latitude])
    names = np.full(len(points), "Outside NYC NTA", dtype=object)
    boroughs = np.full(len(points), "Outside NYC", dtype=object)
    codes = np.full(len(points), "OUT", dtype=object)
    unassigned = np.ones(len(points), dtype=bool)

    for feature in features:
        props = feature["properties"]
        for polygon in polygon_parts(feature["geometry"]):
            outer = np.asarray(polygon[0], dtype=float)
            min_x, min_y = outer.min(axis=0)
            max_x, max_y = outer.max(axis=0)
            candidates = np.flatnonzero(
                unassigned
                & (longitude >= min_x)
                & (longitude <= max_x)
                & (latitude >= min_y)
                & (latitude <= max_y)
            )
            if candidates.size == 0:
                continue
            inside = MplPath(outer).contains_points(points[candidates], radius=1e-12)
            for hole in polygon[1:]:
                if inside.any():
                    hole_inside = MplPath(np.asarray(hole, dtype=float)).contains_points(
                        points[candidates], radius=1e-12
                    )
                    inside &= ~hole_inside
            matched = candidates[inside]
            names[matched] = props["ntaname"]
            boroughs[matched] = props["boroname"]
            codes[matched] = props["nta2020"]
            unassigned[matched] = False
    return names, boroughs, codes


def price_proxy(df: pd.DataFrame) -> pd.Series:
    """Estimate 2016 yellow-cab fare from aggregate trip fields.

    Historical TLC rate proxy:
    - $2.50 initial charge + $0.50 MTA surcharge + $0.30 improvement surcharge.
    - $0.50 per 1/5 mile when average speed exceeds 12 mph, otherwise $0.50
      per minute. Aggregate trip data cannot reproduce mixed meter states.
    - Passenger count has a zero coefficient because standard metered fares
      did not add a per-passenger charge.
    - Tolls, tips, airport, night, and rush-hour surcharges are excluded.
    """
    speed_mph = df["distance"] / (df["duration"] / 3600.0)
    variable = np.where(
        speed_mph > 12.0,
        2.50 * df["distance"],
        0.50 * (df["duration"] / 60.0),
    )
    return pd.Series(3.30 + variable + 0.0 * df["passenger_count"], index=df.index)


def quality_mask(df: pd.DataFrame) -> pd.Series:
    speed_mph = df["distance"] / (df["duration"] / 3600.0)
    geo = (
        df["pickup_longitude"].between(-75.0, -72.0)
        & df["dropoff_longitude"].between(-75.0, -72.0)
        & df["pickup_latitude"].between(39.5, 42.0)
        & df["dropoff_latitude"].between(39.5, 42.0)
    )
    return (
        df["id"].notna()
        & (df["dropoff_datetime"] >= df["pickup_datetime"])
        & df["duration"].between(60, 7200)
        & df["distance"].between(0.25, 50.0)
        & df["passenger_count"].between(1, 6)
        & speed_mph.between(1.0, 80.0)
        & geo
    )


def stats_table(df: pd.DataFrame, label: str) -> pd.DataFrame:
    measures = {
        "duration_seconds": df["duration"],
        "distance_miles": df["distance"],
        "passenger_count": df["passenger_count"],
        "duration_distance_min_per_mile": df["duration_distance_ratio"],
        "price_proxy_usd": df["price_proxy"],
    }
    rows = []
    for measure, values in measures.items():
        clean = values.replace([np.inf, -np.inf], np.nan).dropna()
        sd = clean.std(ddof=1)
        rows.append(
            {
                "population": label,
                "measure": measure,
                "n": int(clean.size),
                "mean": clean.mean(),
                "median": clean.median(),
                "standard_deviation": sd,
                "mean_minus_1sd": clean.mean() - sd,
                "mean_plus_1sd": clean.mean() + sd,
                "mean_minus_2sd": clean.mean() - 2 * sd,
                "mean_plus_2sd": clean.mean() + 2 * sd,
                "minimum": clean.min(),
                "maximum": clean.max(),
            }
        )
    return pd.DataFrame(rows)


def save_table(df: pd.DataFrame, output_dir: Path, filename: str) -> None:
    df.to_csv(output_dir / filename, index=False)


def endpoint_summary(
    df: pd.DataFrame,
    endpoint: str,
    area_lookup: pd.DataFrame,
) -> pd.DataFrame:
    code = f"{endpoint}_nta_code"
    name = f"{endpoint}_nta"
    borough = f"{endpoint}_borough"
    grouped = (
        df.loc[df[code] != "OUT"]
        .groupby([code, name, borough], observed=True)
        .agg(
            ride_count=("id", "size"),
            median_ratio_min_per_mile=("duration_distance_ratio", "median"),
            mean_ratio_min_per_mile=("duration_distance_ratio", "mean"),
            median_distance_miles=("distance", "median"),
            median_duration_minutes=("duration_minutes", "median"),
        )
        .reset_index()
        .rename(columns={code: "nta_code", name: "nta_name", borough: "borough"})
        .merge(area_lookup, on=["nta_code", "nta_name", "borough"], how="left")
    )
    grouped["rides_per_square_mile"] = grouped["ride_count"] / grouped["area_square_miles"]
    grouped["ratio_rank_eligible"] = grouped["ride_count"] >= 1000
    return grouped.sort_values("ride_count", ascending=False)


def age_band(series: pd.Series) -> pd.Series:
    return pd.cut(
        series,
        bins=[17, 24, 34, 44, 54, 64, np.inf],
        labels=["18-24", "25-34", "35-44", "45-54", "55-64", "65+"],
    )


def adoption_summary(survey: pd.DataFrame, segment: str) -> pd.DataFrame:
    valid = survey.dropna(subset=[segment, "Q8_Flying_Taxi"])
    result = (
        valid.groupby(segment, observed=True)
        .agg(
            respondents=("Q8_Flying_Taxi", "size"),
            willing=("Q8_Flying_Taxi", lambda s: int((s == "Y").sum())),
        )
        .reset_index()
        .rename(columns={segment: "segment_value"})
    )
    result.insert(0, "segment", segment)
    result["adoption_rate"] = result["willing"] / result["respondents"]
    return result


def objection_segment(text: object) -> str:
    value = str(text).lower()
    if any(token in value for token in ["unsafe", "danger", "trust the person"]):
        return "Safety and pilot trust"
    if any(token in value for token in ["expensive", "extra money"]):
        return "Price and value"
    if any(token in value for token in ["commute", "efficient", "straightforward"]):
        return "Low perceived need"
    if "crowded" in value:
        return "Airspace externalities"
    return "Other"


def chart_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.titleweight": "bold",
            "axes.titlesize": 14,
            "axes.labelcolor": DECK_COLORS["ink"],
            "text.color": DECK_COLORS["ink"],
            "xtick.color": DECK_COLORS["muted"],
            "ytick.color": DECK_COLORS["muted"],
            "axes.edgecolor": "#d8dde2",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def save_figure(fig: plt.Figure, output_dir: Path, filename: str) -> None:
    fig.canvas.draw()
    fig.savefig(output_dir / filename, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_passengers(df: pd.DataFrame, output_dir: Path) -> None:
    counts = df["passenger_count"].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [DECK_COLORS["teal"] if x in (1, 2) else DECK_COLORS["gold"] for x in counts.index]
    bars = ax.bar(counts.index.astype(str), counts.values, color=colors)
    ax.bar_label(bars, labels=[f"{v/1000:.0f}k" for v in counts.values], padding=3, fontsize=9)
    low_share = counts.reindex([1, 2], fill_value=0).sum() / counts.sum()
    ax.set_title(f"One- and two-passenger rides account for {low_share:.1%} of valid trips")
    ax.set_xlabel("Passenger count")
    ax.set_ylabel("Ride count")
    ax.spines[["top", "right"]].set_visible(False)
    ax.text(0.99, 0.95, "Teal = 1-2 passenger MVP market", transform=ax.transAxes, ha="right", va="top")
    save_figure(fig, output_dir, "passenger_histogram.png")


def plot_temporal(df: pd.DataFrame, output_dir: Path) -> None:
    hours = df.groupby(df["pickup_datetime"].dt.hour).size().reindex(range(24), fill_value=0)
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    days = df.groupby(df["pickup_datetime"].dt.day_name()).size().reindex(day_order)
    months = df.groupby(df["pickup_datetime"].dt.month).size().reindex(range(1, 7))
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    axes[0].plot(hours.index, hours.values, color=DECK_COLORS["teal"], linewidth=3)
    axes[0].fill_between(hours.index, hours.values, color=DECK_COLORS["teal_light"], alpha=0.2)
    axes[0].set_title("Pickups peak at 6-7 PM")
    axes[0].set_xlabel("Hour of day")
    axes[0].set_ylabel("Ride count")

    axes[1].barh(day_order, days.values, color=[DECK_COLORS["gold"]] * 4 + [DECK_COLORS["coral"]] * 2 + [DECK_COLORS["gold"]])
    axes[1].invert_yaxis()
    axes[1].set_title("Friday has the highest volume")
    axes[1].set_xlabel("Ride count")

    axes[2].plot(month_labels, months.values, marker="o", color=DECK_COLORS["coral"], linewidth=3)
    axes[2].set_title("Volume rises through March, then eases")
    axes[2].set_xlabel("2016 month")
    axes[2].set_ylabel("Ride count")
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.15)
    fig.suptitle("Temporal demand supports a Thursday-Saturday evening MVP", fontsize=17, fontweight="bold", y=1.03)
    fig.tight_layout()
    save_figure(fig, output_dir, "temporal_patterns.png")


def draw_choropleth(
    ax: plt.Axes,
    features: list[dict],
    values: dict[str, float],
    title: str,
    cmap_name: str,
    percentile_cap: float = 0.98,
) -> None:
    finite = np.asarray([v for v in values.values() if np.isfinite(v)], dtype=float)
    upper = np.quantile(finite, percentile_cap) if finite.size else 1.0
    norm = Normalize(vmin=0 if finite.min(initial=0) >= 0 else finite.min(), vmax=upper)
    cmap = plt.get_cmap(cmap_name)
    for feature in features:
        code = feature["properties"]["nta2020"]
        value = values.get(code, np.nan)
        face = "#eeeeeb" if not np.isfinite(value) else cmap(norm(min(value, upper)))
        for polygon in polygon_parts(feature["geometry"]):
            outer = np.asarray(polygon[0])
            ax.fill(outer[:, 0], outer[:, 1], facecolor=face, edgecolor="white", linewidth=0.18)
    ax.set_xlim(-74.06, -73.70)
    ax.set_ylim(40.53, 40.92)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=12)


def plot_spatial(
    pickup: pd.DataFrame,
    dropoff: pd.DataFrame,
    features: list[dict],
    output_dir: Path,
) -> None:
    eligible_pickup = pickup[pickup["ratio_rank_eligible"]]
    eligible_dropoff = dropoff[dropoff["ratio_rank_eligible"]]
    panels = [
        (dict(zip(pickup["nta_code"], pickup["rides_per_square_mile"])), "Pickup density per sq. mile", "YlOrRd"),
        (dict(zip(dropoff["nta_code"], dropoff["rides_per_square_mile"])), "Dropoff density per sq. mile", "YlOrRd"),
        (dict(zip(eligible_pickup["nta_code"], eligible_pickup["median_ratio_min_per_mile"])), "Pickup median minutes per mile", "PuBuGn"),
        (dict(zip(eligible_dropoff["nta_code"], eligible_dropoff["median_ratio_min_per_mile"])), "Dropoff median minutes per mile", "PuBuGn"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(10, 10))
    for ax, (values, title, cmap) in zip(axes.flat, panels):
        draw_choropleth(ax, features, values, title, cmap)
    fig.suptitle("Official NYC NTA boundaries reveal concentrated Manhattan opportunity", fontsize=17, fontweight="bold")
    fig.text(0.5, 0.02, "Source overlay: NYC Department of City Planning 2020 NTAs; ratio panels require >=1,000 endpoints.", ha="center", fontsize=9, color=DECK_COLORS["muted"])
    fig.tight_layout(rect=[0, 0.04, 1, 0.96])
    save_figure(fig, output_dir, "spatial_opportunity.png")


def plot_user_adoption(adoption: pd.DataFrame, output_dir: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    segments = ["gender", "age_band", "income"]
    titles = ["Gender", "Age", "Income"]
    for ax, segment, title in zip(axes, segments, titles):
        data = adoption[adoption["segment"] == segment].copy()
        ax.barh(data["segment_value"].astype(str), data["adoption_rate"] * 100, color=DECK_COLORS["teal"])
        for y, value in enumerate(data["adoption_rate"] * 100):
            ax.text(value + 0.8, y, f"{value:.0f}%", va="center", fontsize=9)
        ax.set_xlim(0, 100)
        ax.set_title(title)
        ax.set_xlabel("Willing to use Flyber")
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Stated adoption is broad; demographic differences are modest", fontsize=17, fontweight="bold")
    fig.tight_layout()
    save_figure(fig, output_dir, "user_adoption_segments.png")


def plot_wtp(survey: pd.DataFrame, output_dir: Path) -> None:
    yes = survey[survey["Q8_Flying_Taxi"] == "Y"].dropna(subset=["Q9_If_Yes"])
    age = yes.groupby("age_band", observed=True)["Q9_If_Yes"].agg(["mean", "median", "count"]).reset_index()
    income_order = ["$0 - $20,000", "$20,001 - $40,000", "$40,001 - $80,000", "$80,000 - $120,000", "$120,000 - $200,000", "> $200,000"]
    income = yes.groupby("Q4_Income")["Q9_If_Yes"].agg(["mean", "median", "count"]).reindex(income_order).reset_index()
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    axes[0].bar(age["age_band"].astype(str), age["median"], color=DECK_COLORS["gold"])
    axes[0].axhline(yes["Q9_If_Yes"].median(), color=DECK_COLORS["ink"], linestyle="--", linewidth=1)
    axes[0].set_title("Median willingness to pay by age")
    axes[0].set_ylabel("USD per mile")
    axes[1].barh(income["Q4_Income"], income["median"], color=DECK_COLORS["coral"])
    axes[1].set_title("Median willingness to pay by income")
    axes[1].set_xlabel("USD per mile")
    axes[1].invert_yaxis()
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.15)
    fig.suptitle(f"Willing respondents report a ${yes['Q9_If_Yes'].median():.0f}/mile median", fontsize=17, fontweight="bold")
    fig.tight_layout()
    save_figure(fig, output_dir, "willingness_to_pay.png")


def plot_objections(survey: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    objections = survey[survey["Q8_Flying_Taxi"] == "N"].copy()
    objections["objection_segment"] = objections["Q10_If_No"].map(objection_segment)
    summary = objections["objection_segment"].value_counts().rename_axis("objection_segment").reset_index(name="respondents")
    summary["share"] = summary["respondents"] / summary["respondents"].sum()
    fig, ax = plt.subplots(figsize=(9, 5))
    data = summary.sort_values("respondents")
    bars = ax.barh(data["objection_segment"], data["respondents"], color=DECK_COLORS["coral"])
    ax.bar_label(bars, labels=[f"{x:.0%}" for x in data["share"]], padding=4)
    ax.set_title("Safety and pilot trust dominate negative sentiment")
    ax.set_xlabel("Respondents unwilling to use Flyber")
    ax.spines[["top", "right"]].set_visible(False)
    save_figure(fig, output_dir, "objections.png")
    return summary


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_style()

    taxi_columns = [
        "id", "vendor_id", "pickup_datetime", "dropoff_datetime", "passenger_count",
        "pickup_longitude", "pickup_latitude", "dropoff_longitude", "dropoff_latitude",
        "store_and_fwd_flag", "duration", "distance",
    ]
    taxi = pd.read_csv(args.taxi, usecols=taxi_columns)
    for field in ["pickup_datetime", "dropoff_datetime"]:
        taxi[field] = pd.to_datetime(taxi[field], format="%m/%d/%y %H:%M", errors="raise")
    taxi["duration_minutes"] = taxi["duration"] / 60.0
    taxi["duration_distance_ratio"] = taxi["duration_minutes"] / taxi["distance"].replace(0, np.nan)
    taxi["price_proxy"] = price_proxy(taxi)
    taxi["speed_mph"] = taxi["distance"] / (taxi["duration"] / 3600.0)
    taxi["analysis_valid"] = quality_mask(taxi)

    nta_path = ensure_nta(Path(args.nta_geojson) if args.nta_geojson else None, output_dir)
    nta = json.loads(nta_path.read_text(encoding="utf-8"))
    features = nta["features"]
    taxi["pickup_nta"], taxi["pickup_borough"], taxi["pickup_nta_code"] = assign_nta(
        taxi["pickup_longitude"].to_numpy(), taxi["pickup_latitude"].to_numpy(), features
    )
    taxi["dropoff_nta"], taxi["dropoff_borough"], taxi["dropoff_nta_code"] = assign_nta(
        taxi["dropoff_longitude"].to_numpy(), taxi["dropoff_latitude"].to_numpy(), features
    )

    area_lookup = pd.DataFrame(
        [
            {
                "nta_code": f["properties"]["nta2020"],
                "nta_name": f["properties"]["ntaname"],
                "borough": f["properties"]["boroname"],
                "area_square_miles": float(f["properties"]["shape_area"]) / 27_878_400.0,
            }
            for f in features
        ]
    )

    valid = taxi[taxi["analysis_valid"]].copy()
    descriptive = pd.concat([stats_table(taxi, "raw_full_dataset"), stats_table(valid, "operational_quality_subset")], ignore_index=True)
    save_table(descriptive, output_dir, "descriptive_statistics.csv")

    exclusions = pd.DataFrame(
        {
            "check": [
                "Total records", "Unique primary keys", "Operational-quality records",
                "Excluded records", "Zero-distance records", "Passenger count outside 1-6",
                "Duration outside 60-7200 seconds", "Distance outside 0.25-50 miles",
                "Average speed outside 1-80 mph", "Pickup outside NYC NTA", "Dropoff outside NYC NTA",
            ],
            "records": [
                len(taxi), taxi["id"].nunique(), len(valid), len(taxi) - len(valid),
                int((taxi["distance"] == 0).sum()), int((~taxi["passenger_count"].between(1, 6)).sum()),
                int((~taxi["duration"].between(60, 7200)).sum()), int((~taxi["distance"].between(0.25, 50)).sum()),
                int((~taxi["speed_mph"].between(1, 80)).sum()), int((taxi["pickup_nta_code"] == "OUT").sum()),
                int((taxi["dropoff_nta_code"] == "OUT").sum()),
            ],
        }
    )
    save_table(exclusions, output_dir, "data_quality_reconciliation.csv")

    passengers = valid["passenger_count"].value_counts().sort_index().rename_axis("passenger_count").reset_index(name="ride_count")
    passengers["share"] = passengers["ride_count"] / passengers["ride_count"].sum()
    save_table(passengers, output_dir, "passenger_counts.csv")

    hourly = valid.groupby(valid["pickup_datetime"].dt.hour).size().rename_axis("hour").reset_index(name="ride_count")
    daily = valid.groupby(valid["pickup_datetime"].dt.day_name()).size().rename_axis("day_of_week").reset_index(name="ride_count")
    monthly = valid.groupby(valid["pickup_datetime"].dt.to_period("M").astype(str)).size().rename_axis("month").reset_index(name="ride_count")
    save_table(hourly, output_dir, "pickups_by_hour.csv")
    save_table(daily, output_dir, "pickups_by_day.csv")
    save_table(monthly, output_dir, "pickups_by_month.csv")

    pickup_summary = endpoint_summary(valid, "pickup", area_lookup)
    dropoff_summary = endpoint_summary(valid, "dropoff", area_lookup)
    save_table(pickup_summary, output_dir, "pickup_neighborhoods.csv")
    save_table(dropoff_summary, output_dir, "dropoff_neighborhoods.csv")

    survey = pd.read_csv(args.survey)
    survey["age_band"] = age_band(survey["Q3_Age"])
    survey["gender"] = survey["Q2_Gender"].map({"F": "Female", "M": "Male"}).fillna(survey["Q2_Gender"])
    survey["income"] = survey["Q4_Income"]
    adoption = pd.concat(
        [adoption_summary(survey, x) for x in ["gender", "age_band", "income", "Q5_Neighborhood"]],
        ignore_index=True,
    )
    save_table(adoption, output_dir, "survey_adoption_segments.csv")

    yes = survey[survey["Q8_Flying_Taxi"] == "Y"].copy()
    wtp = pd.concat(
        [
            yes.groupby("age_band", observed=True)["Q9_If_Yes"].agg(["count", "mean", "median", "std"]).reset_index().assign(segment="age_band").rename(columns={"age_band": "segment_value"}),
            yes.groupby("income", observed=True)["Q9_If_Yes"].agg(["count", "mean", "median", "std"]).reset_index().assign(segment="income").rename(columns={"income": "segment_value"}),
            yes.groupby("gender", observed=True)["Q9_If_Yes"].agg(["count", "mean", "median", "std"]).reset_index().assign(segment="gender").rename(columns={"gender": "segment_value"}),
        ],
        ignore_index=True,
    )
    save_table(wtp[["segment", "segment_value", "count", "mean", "median", "std"]], output_dir, "survey_willingness_to_pay.csv")
    objections = plot_objections(survey, output_dir)
    save_table(objections, output_dir, "survey_objections.csv")

    plot_passengers(valid, output_dir)
    plot_temporal(valid, output_dir)
    plot_spatial(pickup_summary, dropoff_summary, features, output_dir)
    plot_user_adoption(adoption, output_dir)
    plot_wtp(survey, output_dir)

    top_pickup_density = pickup_summary.nlargest(10, "rides_per_square_mile").to_dict("records")
    top_dropoff_density = dropoff_summary.nlargest(10, "rides_per_square_mile").to_dict("records")
    top_pickup_ratio = pickup_summary[pickup_summary["ratio_rank_eligible"]].nlargest(10, "median_ratio_min_per_mile").to_dict("records")
    top_dropoff_ratio = dropoff_summary[dropoff_summary["ratio_rank_eligible"]].nlargest(10, "median_ratio_min_per_mile").to_dict("records")
    q8_valid = survey["Q8_Flying_Taxi"].dropna()
    summary = {
        "data_scope": {
            "records": int(len(taxi)),
            "unique_ids": int(taxi["id"].nunique()),
            "record_definition": "One completed taxi trip with pickup/dropoff time, coordinates, passengers, duration, and distance.",
            "primary_key": "id",
            "pickup_start": taxi["pickup_datetime"].min().isoformat(),
            "pickup_end": taxi["pickup_datetime"].max().isoformat(),
            "raw_coordinate_bounds": {
                "pickup_longitude": [float(taxi["pickup_longitude"].min()), float(taxi["pickup_longitude"].max())],
                "pickup_latitude": [float(taxi["pickup_latitude"].min()), float(taxi["pickup_latitude"].max())],
                "dropoff_longitude": [float(taxi["dropoff_longitude"].min()), float(taxi["dropoff_longitude"].max())],
                "dropoff_latitude": [float(taxi["dropoff_latitude"].min()), float(taxi["dropoff_latitude"].max())],
            },
            "operational_quality_records": int(len(valid)),
            "operational_quality_share": float(len(valid) / len(taxi)),
        },
        "price_proxy": {
            "formula": "3.30 + IF average_speed_mph > 12 THEN 2.50*distance_miles ELSE 0.50*duration_minutes END + 0*passenger_count",
            "limitations": "Aggregate proxy excludes tolls, tips, airport/night/rush surcharges and cannot reproduce mixed time-distance meter states.",
        },
        "passenger_market": {
            "one_to_two_share": float(passengers.loc[passengers["passenger_count"].isin([1, 2]), "ride_count"].sum() / passengers["ride_count"].sum())
        },
        "temporal": {
            "top_hours": hourly.nlargest(5, "ride_count").to_dict("records"),
            "top_days": daily.nlargest(7, "ride_count").to_dict("records"),
            "months": monthly.to_dict("records"),
        },
        "spatial": {
            "boundary_source": NTA_URL,
            "boundary_caveat": "2020 NTA boundaries are used to classify 2016 ride endpoints.",
            "top_pickup_density": top_pickup_density,
            "top_dropoff_density": top_dropoff_density,
            "top_pickup_ratio": top_pickup_ratio,
            "top_dropoff_ratio": top_dropoff_ratio,
        },
        "survey": {
            "respondents": int(len(survey)),
            "valid_flying_taxi_answers": int(len(q8_valid)),
            "willing_count": int((q8_valid == "Y").sum()),
            "willing_share": float((q8_valid == "Y").mean()),
            "willing_price_mean": float(yes["Q9_If_Yes"].mean()),
            "willing_price_median": float(yes["Q9_If_Yes"].median()),
            "objection_segments": objections.to_dict("records"),
        },
    }
    (output_dir / "analysis_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if args.write_tableau:
        tableau_columns = [
            "id", "pickup_datetime", "dropoff_datetime", "passenger_count",
            "pickup_longitude", "pickup_latitude", "dropoff_longitude", "dropoff_latitude",
            "duration", "duration_minutes", "distance", "speed_mph",
            "duration_distance_ratio", "price_proxy", "analysis_valid",
            "pickup_nta_code", "pickup_nta", "pickup_borough",
            "dropoff_nta_code", "dropoff_nta", "dropoff_borough",
        ]
        taxi[tableau_columns].to_csv(output_dir / "tableau_taxi_enriched.csv", index=False)


if __name__ == "__main__":
    main()
