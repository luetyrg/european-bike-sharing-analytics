from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
FULL_RAW_DIR = RAW_DIR / "full"
SAMPLE_RAW_DIR = RAW_DIR / "sample"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
SQL_DIR = ROOT / "sql"
FIGURES_DIR = ROOT / "reports" / "figures"

DATASET_URL = (
    "https://github.com/TUMFTM/european-bike-sharing-dataset/"
    "raw/refs/heads/main/full/dataset.zip"
)
SAMPLE_BASE_URL = (
    "https://raw.githubusercontent.com/TUMFTM/"
    "european-bike-sharing-dataset/main/sample"
)
ARCHIVE_PATH = RAW_DIR / "dataset.zip"
SOURCE_TABLES = ("trips.csv", "cities.csv", "stations.csv", "bikes.csv", "bike_types.csv")

CANDIDATE_CITY_GROUPS = {
    "Berlin": ("Berlin",),
    "Warszawa": ("Warszawa", "Warszawa - 2023"),
    "Dresden": ("Dresden",),
    "Bilbao": ("Bilbao",),
    "Köln": ("Köln",),
    "Frankfurt": ("Frankfurt",),
}
PREFERRED_CITIES = ("Berlin", "Warszawa", "Dresden", "Bilbao")
ALTERNATE_CITIES = ("Köln", "Frankfurt")

MIN_DURATION_SECONDS = 60
MAX_DURATION_SECONDS = 6 * 60 * 60
MAX_DISTANCE_METERS = 100_000
MAX_SPEED_KMH = 60

MIN_SELECTION_TRIPS = 1_000
MIN_SELECTION_ACTIVE_DAYS = 14
MIN_VALID_DURATION_SHARE = 0.80

CITY_COLORS = {
    "Berlin": "#2563EB",
    "Warszawa": "#DC2626",
    "Dresden": "#16A34A",
    "Bilbao": "#F59E0B",
    "Köln": "#7C3AED",
    "Frankfurt": "#0891B2",
}


def ensure_directories() -> None:
    for path in (RAW_DIR, FULL_RAW_DIR, INTERIM_DIR, PROCESSED_DIR, FIGURES_DIR):
        path.mkdir(parents=True, exist_ok=True)
