"""
PitchGuard – Data Scraper
Cron-scheduled scraper for Transfermarkt / FBref player stats.
"""

import time
import requests
from bs4 import BeautifulSoup
from typing import Optional

# ── Configuration ─────────────────────────────────────────────────────
TRANSFERMARKT_BASE = "https://www.transfermarkt.com"
FBREF_BASE = "https://fbref.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

REQUEST_DELAY_SEC = 3  # polite delay between requests


# ── Transfermarkt helpers ─────────────────────────────────────────────
def scrape_player_injuries(player_slug: str) -> list[dict]:
    """
    Scrape the injury history table for a given player.
    Example slug: "erling-haaland/profil/spieler/418560"
    """
    url = f"{TRANSFERMARKT_BASE}/{player_slug}/verletzungen"
    # TODO: implement full parsing
    # resp = requests.get(url, headers=HEADERS)
    # soup = BeautifulSoup(resp.text, "html.parser")
    print(f"[scraper] Would scrape injuries from {url}")
    return []


def scrape_player_market_value(player_slug: str) -> Optional[float]:
    """Scrape current market value in EUR."""
    url = f"{TRANSFERMARKT_BASE}/{player_slug}"
    # TODO: implement
    print(f"[scraper] Would scrape market value from {url}")
    return None


# ── FBref helpers ─────────────────────────────────────────────────────
def scrape_player_match_logs(fbref_id: str, season: str = "2024-2025") -> list[dict]:
    """
    Scrape per-match stats (minutes, distance, sprints, etc.)
    from FBref for a given player + season.
    """
    url = f"{FBREF_BASE}/en/players/{fbref_id}/matchlogs/{season}/summary"
    # TODO: implement full parsing
    print(f"[scraper] Would scrape match logs from {url}")
    return []


# ── Orchestrator ──────────────────────────────────────────────────────
def run_daily_scrape(player_list: list[dict]) -> None:
    """
    Run the full daily scrape for every player in `player_list`.
    Each entry should have keys: transfermarkt_slug, fbref_id, name.
    """
    for player in player_list:
        name = player.get("name", "unknown")
        print(f"[scraper] Processing {name} …")

        injuries = scrape_player_injuries(player["transfermarkt_slug"])
        market_val = scrape_player_market_value(player["transfermarkt_slug"])
        match_logs = scrape_player_match_logs(player["fbref_id"])

        # TODO: persist to database / CSV / parquet
        print(
            f"  → injuries={len(injuries)}, "
            f"market_val={market_val}, "
            f"match_logs={len(match_logs)}"
        )

        time.sleep(REQUEST_DELAY_SEC)

    print("[scraper] Daily scrape complete.")


# ── CLI entry-point ──────────────────────────────────────────────────
if __name__ == "__main__":
    # Example: run with a small test list
    sample_players = [
        {
            "name": "Erling Haaland",
            "transfermarkt_slug": "erling-haaland/profil/spieler/418560",
            "fbref_id": "1f44ac21",
        },
    ]
    run_daily_scrape(sample_players)
