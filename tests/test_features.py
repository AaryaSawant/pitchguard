"""
Tests for feature engineering pipeline.
"""

import csv

import pandas as pd

from src.features.build_features import compute_congestion, encode_injury_history


def test_encode_injury_history_empty():
    result = encode_injury_history(pd.DataFrame())
    assert result["injury_count_2y"] == 0
    assert result["has_acl"] == 0
    assert result["has_hamstring"] == 0


def test_encode_injury_history_with_acl():
    df = pd.DataFrame(
        [
            {
                "from_date": pd.Timestamp.now().strftime("%Y-%m-%d"),
                "to_date": pd.Timestamp.now().strftime("%Y-%m-%d"),
                "injury_type": "Anterior Cruciate Ligament",
                "games_missed": "8",
            }
        ]
    )
    result = encode_injury_history(df)
    assert result["has_acl"] == 1
    assert result["injury_count_2y"] == 1


def test_encode_injury_history_hamstring():
    df = pd.DataFrame(
        [
            {
                "from_date": pd.Timestamp.now().strftime("%Y-%m-%d"),
                "to_date": pd.Timestamp.now().strftime("%Y-%m-%d"),
                "injury_type": "Hamstring Strain",
                "games_missed": "3",
            }
        ]
    )
    result = encode_injury_history(df)
    assert result["has_hamstring"] == 1
    assert result["has_acl"] == 0


def test_compute_congestion():
    reference = pd.Timestamp("2024-03-20")
    logs = pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2024-03-10", "2024-03-15", "2024-03-01", "2024-02-10"]
            ),
            "minutes_played": [90, 75, 60, 90],
            "player_id": ["p1"] * 4,
        }
    )
    result = compute_congestion(logs, reference)
    assert result["games_last_14d"] == 2
    assert result["minutes_last_30d"] == 225


def test_surface_flag_range():
    """Surface type should only be 0 (grass) or 1 (astro)."""
    with open("data/surface_mapping/stadium_surfaces.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            assert row["surface_type"] in (
                "0",
                "1",
            ), f"Invalid surface_type in row: {row}"
