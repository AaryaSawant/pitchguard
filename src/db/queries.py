from dotenv import load_dotenv

load_dotenv()

import os  # noqa: E402
from supabase import create_client, Client  # noqa: E402

"""
PitchGuard — Database Queries
File: src/db/queries.py

Column name reference (VERIFIED against real schema errors and
create_player_features_table.sql — do not "fix" this back to something
that looks more consistent without re-checking against Supabase):

  players table       -> tm_player_id
  injuries table       -> player_tm_id
  player_stats table  -> player_tm_id
  player_features table -> tm_player_id   (matches players convention,
                            NOT injuries/player_stats — this table was
                            created fresh via SQL using tm_player_id,
                            confirmed by the "column player_features.
                            player_tm_id does not exist" error)
"""

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
        if not url or not key:
            raise EnvironmentError(
                "Supabase credentials not set.\n"
                "  PowerShell: $env:SUPABASE_URL='...'; $env:SUPABASE_KEY='...'\n"
                "Or add them to a .env file and load with python-dotenv."
            )
        _client = create_client(url, key)
    return _client


# ── Clubs ─────────────────────────────────────────────────────────────────────


def get_all_clubs() -> list[str]:
    """Return sorted list of all unique club names, paginated past
    Supabase's default 1000-row limit (this was the earlier "only 36 of 97
    clubs" bug — do not remove the pagination loop)."""
    sb = get_supabase()
    all_club_names: set[str] = set()
    page_size = 1000
    start = 0
    while True:
        page = (
            sb.table("players")
            .select("club_name")
            .range(start, start + page_size - 1)
            .execute()
            .data
        )
        if not page:
            break
        all_club_names.update(d["club_name"] for d in page if d.get("club_name"))
        if len(page) < page_size:
            break
        start += page_size
    return sorted(all_club_names)


# ── Squad ─────────────────────────────────────────────────────────────────────


def get_squad(club_name: str) -> list[dict]:
    """Return all player rows for a given club. players table uses tm_player_id."""
    sb = get_supabase()
    return sb.table("players").select("*").eq("club_name", club_name).execute().data


def get_player_by_id(tm_player_id: str) -> dict | None:
    """Return a single player row. players table uses tm_player_id."""
    sb = get_supabase()
    rows = (
        sb.table("players")
        .select("*")
        .eq("tm_player_id", tm_player_id)
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


# ── Player Features ───────────────────────────────────────────────────────────


def get_player_features(tm_player_id: str) -> dict | None:
    """Return engineered model features for one player.
    player_features table uses tm_player_id (NOT player_tm_id — verified
    against the real Postgres schema error)."""
    sb = get_supabase()
    rows = (
        sb.table("player_features")
        .select("*")
        .eq("tm_player_id", tm_player_id)
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


def get_squad_features(player_ids: list[str]) -> dict[str, dict]:
    """
    Batch-fetch engineered features for a list of tm_player_ids.
    Returns {tm_player_id: features_dict}.
    player_features table uses tm_player_id (see note above).
    Wrapped in try/except so a missing/misconfigured table degrades to
    "no features found" (predictor falls back to computed defaults) rather
    than crashing the whole /squad endpoint.
    """
    sb = get_supabase()
    if not player_ids:
        return {}
    try:
        rows = (
            sb.table("player_features")
            .select("*")
            .in_("tm_player_id", player_ids)
            .execute()
            .data
        )
        return {r["tm_player_id"]: r for r in rows}
    except Exception as exc:
        print(
            f"⚠️  get_squad_features failed ({exc}) — falling back to empty features for this squad."
        )
        return {}


# ── Injuries ──────────────────────────────────────────────────────────────────


def get_player_injuries(player_tm_id: str) -> list[dict]:
    """Return all injuries for a player. injuries table uses player_tm_id."""
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
    Batch-fetch injuries for a whole squad.
    players table  -> tm_player_id  (used to get the IDs)
    injuries table -> player_tm_id  (used to filter injuries)
    These are genuinely different column names on different tables —
    this isn't a bug, don't "fix" them to match.
    """
    sb = get_supabase()
    players = get_squad(club_name)

    ids = [p["tm_player_id"] for p in players if p.get("tm_player_id")]
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
    """Return season stats for a player. player_stats table uses player_tm_id."""
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


def get_stadium_surface(club_name: str) -> int | None:
    """Return surface_type (0=grass, 1=artificial) for a club's home stadium."""
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
    """Return full stadium surfaces table."""
    sb = get_supabase()
    return sb.table("stadiums").select("*").execute().data


# ── Connection test ───────────────────────────────────────────────────────────


def test_connection():
    print("Testing Supabase connection...")
    try:
        clubs = get_all_clubs()
        print(f"Connected. Found {len(clubs)} clubs.")
        if clubs:
            print(f"  First 5: {clubs[:5]}")
    except EnvironmentError as e:
        print(f"Credential error:\n{e}")
    except Exception as e:
        print(f"Connection failed: {e}")


if __name__ == "__main__":
    test_connection()
