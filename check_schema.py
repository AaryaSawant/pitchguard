"""
One-off diagnostic — run this to see the real column names on the players
table, so we know what to group clubs by league with.

Run:
    python check_schema.py
"""

from src.db.queries import get_supabase

sb = get_supabase()
row = sb.table("players").select("*").limit(1).execute().data
if row:
    print("players table columns:")
    for k, v in row[0].items():
        print(f"  {k}: {v!r}")
else:
    print("No rows returned — table might be empty or name is wrong.")

print()

stadium_row = sb.table("stadiums").select("*").limit(1).execute().data
if stadium_row:
    print("stadiums table columns:")
    for k, v in stadium_row[0].items():
        print(f"  {k}: {v!r}")
