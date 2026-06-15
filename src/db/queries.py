"""
PitchGuard — Database Queries
File: src/db/queries.py

All Supabase calls live here. The dashboard and predictor import from this module.

Quick connection test:
    python src/db/queries.py
"""

import os
from supabase import create_client, Client

# ── Connection ────────────────────────────────────────────────────────────────
# Set these in your environment or a .env file — never hardcode credentials.
# Windows (cmd):    set SUPABASE_URL=https://xxxx.supabase.co
#                   set SUPABASE_KEY=your-anon-key
# Windows (PS):     $env:SUPABASE_URL="https://xxxx.supabase.co"
#                   $env:SUPABASE_KEY="your-anon-key"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

_client: Client | None = None


def get_supabase() -> Client:
    """Return a cached Supabase client. Raises clearly if credentials are missing."""
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise EnvironmentError(
                "Supabase credentials not set.\n"
                "  Windows CMD:  set SUPABASE_URL=... && set SUPABASE_KEY=...\n"
                "  PowerShell:   $env:SUPABASE_URL='...'; $env:SUPABASE_KEY='...'\n"
                "Or add them to a .env file and load with python-dotenv."
            )
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


# ── Clubs ─────────────────────────────────────────────────────────────────────


def get_all_clubs() -> list[str]:
    """Return sorted list of all unique club names in the players table."""
    sb = get_supabase()
    data = sb.table("players").select("club_name").execute().data
    return sorted(set(d["club_name"] for d in data if d.get("club_name")))


def get_clubs_by_league(league: str) -> list[str]:
    """Return clubs filtered by league name (e.g. 'Premier League')."""
    sb = get_supabase()
    data = sb.table("players").select("club_name").eq("league", league).execute().data
    return sorted(set(d["club_name"] for d in data if d.get("club_name")))


# ── Squad ─────────────────────────────────────────────────────────────────────


def get_squad(club_name: str) -> list[dict]:
    """Return all player rows for a given club."""
    sb = get_supabase()
    return sb.table("players").select("*").eq("club_name", club_name).execute().data


def get_player_by_id(player_tm_id: str) -> dict | None:
    """Return a single player row by Transfermarkt ID, or None if not found."""
    sb = get_supabase()
    rows = (
        sb.table("players")
        .select("*")
        .eq("player_tm_id", player_tm_id)
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


# ── Injuries ──────────────────────────────────────────────────────────────────


def get_player_injuries(player_tm_id: str) -> list[dict]:
    """Return all injury records for a player, newest first."""
    sb = get_supabase()
    return (
        sb.table("injuries")
        .select("*")
        .eq("player_tm_id", player_tm_id)
        .order("injury_date", desc=True)
        .execute()
        .data
    )


def get_squad_injuries(club_name: str) -> list[dict]:
    """
    Return injury records for an entire squad in one query.
    Joins via player_tm_id — avoids N+1 calls from the dashboard.
    """
    sb = get_supabase()
    # Get player IDs for the club first
    players = get_squad(club_name)
    ids = [p["player_tm_id"] for p in players if p.get("player_tm_id")]
    if not ids:
        return []
    return (
        sb.table("injuries")
        .select("*")
        .in_("player_tm_id", ids)
        .order("injury_date", desc=True)
        .execute()
        .data
    )


# ── Stats ─────────────────────────────────────────────────────────────────────


def get_player_stats(player_tm_id: str) -> list[dict]:
    """Return all season stats rows for a player."""
    sb = get_supabase()
    return (
        sb.table("player_stats")
        .select("*")
        .eq("player_tm_id", player_tm_id)
        .order("season", desc=True)
        .execute()
        .data
    )


# ── Stadiums ──────────────────────────────────────────────────────────────────


def get_stadium_surface(club_name: str) -> str | None:
    """Return 'grass' or 'artificial' for a club's home stadium, or None."""
    sb = get_supabase()
    rows = (
        sb.table("stadiums")
        .select("surface_type")
        .eq("club_name", club_name)
        .limit(1)
        .execute()
        .data
    )
    return rows[0]["surface_type"] if rows else None


def get_all_surfaces() -> list[dict]:
    """Return the full stadium surfaces lookup table (useful for the dashboard map)."""
    sb = get_supabase()
    return sb.table("stadiums").select("*").execute().data


# ── Connection test ───────────────────────────────────────────────────────────


def test_connection():
    print("Testing Supabase connection ...")
    try:
        clubs = get_all_clubs()
        print(f"✅ Connected. Found {len(clubs)} clubs in players table.")
        if clubs:
            print(f"   First 5: {clubs[:5]}")
    except EnvironmentError as e:
        print(f"❌ Credential error:\n{e}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")


if __name__ == "__main__":
    test_connection()
