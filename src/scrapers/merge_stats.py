"""
merge_stats.py
--------------
Merges master_stats_from_csvs.csv and master_stats_from_excel.csv
into a single master_stats_final.csv with uniform columns.

Final schema: player_name, tm_id, season, appearances, minutes
"""

import csv
from pathlib import Path

CSV_SOURCE = Path(
    r"C:\Users\Aarya\Downloads\Pitchguard\pitchguard\src\scrapers\data\raw\master_stats_from_csvs.csv"
)
EXCEL_SOURCE = Path(
    r"C:\Users\Aarya\Downloads\Pitchguard\pitchguard\src\scrapers\data\raw\master_stats_from_excel.csv"
)
OUTPUT = Path(
    r"C:\Users\Aarya\Downloads\Pitchguard\pitchguard\src\scrapers\data\raw\master_stats_final.csv"
)

FINAL_COLS = ["player_name", "tm_id", "season", "appearances", "minutes"]


def main():
    all_rows = []

    # Load CSVs — drop player_no
    with open(CSV_SOURCE, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            all_rows.append({c: r[c] for c in FINAL_COLS})

    csv_count = len(all_rows)
    print(f"CSVs   : {csv_count:,} rows loaded")

    # Load Excel — already has correct columns
    with open(EXCEL_SOURCE, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            all_rows.append({c: r[c] for c in FINAL_COLS})

    excel_count = len(all_rows) - csv_count
    print(f"Excel  : {excel_count:,} rows loaded")

    # Write final
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FINAL_COLS)
        writer.writeheader()
        writer.writerows(all_rows)

    unique_players = len({r["tm_id"] for r in all_rows})
    unique_seasons = sorted({r["season"] for r in all_rows})

    print("\n✅ master_stats_final.csv written")
    print(f"   Total rows     : {len(all_rows):,}")
    print(f"   Unique players : {unique_players:,}")
    print(f"   Seasons        : {unique_seasons}")
    print(f"\n   Path: {OUTPUT}")


if __name__ == "__main__":
    main()
