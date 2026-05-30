"""
FBref Scraper
-------------
Scrapes match logs and player workload data from FBref
for fixture congestion and minutes-played calculations.

Usage:
    python src/scrapers/fbref_scraper.py --league pl --season 2023-2024
"""

import argparse
import time
import logging
from pathlib import Path

import requests
import pandas as pd
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PitchGuard Research Bot/1.0; "
        "+https://github.com/YOUR_USERNAME/pitchguard)"
    )
}

# FBref league codes
FBREF_LEAGUES = {
    "pl": 9,
    "la_liga": 12,
    "bundesliga": 20,
    "serie_a": 11,
    "ligue_1": 13,
    "super_lig": 26,
}

DELAY_SECONDS = 3  # FBref rate-limits aggressively


def get_player_match_log(player_fbref_id: str, season: str) -> pd.DataFrame:
    """
    Fetch a player's match-by-match log for a given season.
    Returns DataFrame with columns: date, opponent, venue, minutes_played, result.
    """
    url = (
        f"https://fbref.com/en/players/{player_fbref_id}/"
        f"matchlogs/{season}/summary/"
    )
    time.sleep(DELAY_SECONDS)
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    table = soup.find("table", {"id": "matchlogs_dom"})
    if table is None:
        logger.warning(f"No match log table found for {player_fbref_id}")
        return pd.DataFrame()

    rows = []
    for row in table.select("tbody tr:not(.thead)"):
        date_cell = row.find("td", {"data-stat": "date"})
        venue_cell = row.find("td", {"data-stat": "venue"})
        minutes_cell = row.find("td", {"data-stat": "minutes"})
        opponent_cell = row.find("td", {"data-stat": "opponent"})
        result_cell = row.find("td", {"data-stat": "result"})

        if not date_cell:
            continue

        rows.append(
            {
                "date": date_cell.text.strip(),
                "venue": venue_cell.text.strip() if venue_cell else None,
                "opponent": opponent_cell.text.strip() if opponent_cell else None,
                "minutes_played": minutes_cell.text.strip() if minutes_cell else None,
                "result": result_cell.text.strip() if result_cell else None,
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["minutes_played"] = pd.to_numeric(df["minutes_played"], errors="coerce")
        df["player_id"] = player_fbref_id
    return df


def compute_congestion(match_log: pd.DataFrame, reference_date: pd.Timestamp) -> dict:
    """
    Given a player's match log, compute workload features relative to a reference date
    (typically the upcoming match date).

    Returns a dict of computed features.
    """
    past = match_log[match_log["date"] < reference_date].copy()
    past = past.sort_values("date", ascending=False)

    last_30_days = past[past["date"] >= reference_date - pd.Timedelta(days=30)]
    last_14_days = past[past["date"] >= reference_date - pd.Timedelta(days=14)]

    return {
        "minutes_last_30d": last_30_days["minutes_played"].sum(),
        "games_last_14d": len(last_14_days),
        "season_minutes": past["minutes_played"].sum(),
        "avg_minutes_per_game": (past["minutes_played"].mean() if len(past) > 0 else 0),
        "days_since_last_game": (
            (reference_date - past.iloc[0]["date"]).days if len(past) > 0 else None
        ),
    }


def main(league: str, season: str, output_dir: str) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    league_id = FBREF_LEAGUES.get(league)
    if not league_id:
        raise ValueError(
            f"Unknown league '{league}'. Valid: {list(FBREF_LEAGUES.keys())}"
        )

    logger.info(f"FBref scraper ready for league={league}, season={season}")
    logger.info("Provide player FBref IDs (from squad data) to fetch individual logs.")
    logger.info(f"Output will be saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape FBref match logs")
    parser.add_argument("--league", required=True, choices=FBREF_LEAGUES.keys())
    parser.add_argument("--season", default="2023-2024")
    parser.add_argument("--output", default="data/raw/")
    args = parser.parse_args()
    main(args.league, args.season, args.output)
