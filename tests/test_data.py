"""Schema and canonical-city tests using tiny in-memory inputs."""

import pandas as pd

from src.data import build_city_map


def test_warszawa_group_preserves_both_source_ids() -> None:
    rows = [
        (362, "Berlin", "Europe/Berlin", "DE"),
        (210, "Warszawa", "Europe/Warsaw", "PL"),
        (812, "Warszawa - 2023", "Europe/Warsaw", "PL"),
        (685, "Dresden", "Europe/Berlin", "DE"),
        (532, "Bilbao", "Europe/Berlin", "ES"),
        (14, "Köln", "Europe/Berlin", "DE"),
        (8, "Frankfurt", "Europe/Berlin", "DE"),
    ]
    cities = pd.DataFrame(rows, columns=["id", "name", "timezone", "country"])
    city_map = build_city_map(cities)
    warszawa_ids = set(city_map.loc[city_map["city"] == "Warszawa", "city_id"])
    assert warszawa_ids == {210, 812}

