"""
merge_batch2.py
---------------
Reads all 228 CSVs from player_stats_output/,
appends to master_stats_final.csv.
New CSVs already have correct headers: player_name, tm_id, season, appearances, minutes
"""

import csv
from pathlib import Path

OUTPUT_DIR = Path(
    r"C:\Users\Aarya\Downloads\Pitchguard\pitchguard\src\scrapers\data\raw\player_stats_output"
)
MASTER_CSV = Path(
    r"C:\Users\Aarya\Downloads\Pitchguard\pitchguard\src\scrapers\data\raw\master_stats_final.csv"
)

FINAL_COLS = ["player_name", "tm_id", "season", "appearances", "minutes"]

TARGET_SEASONS = {
    "19/20",
    "20/21",
    "21/22",
    "22/23",
    "23/24",
    "24/25",
    "25/26",
    "2019",
    "2020",
    "2021",
    "2022",
    "2023",
    "2024",
    "2025",
    "2026",
}


def main():
    # Load existing master
    existing = []
    with open(MASTER_CSV, newline="", encoding="utf-8") as f:
        existing = list(csv.DictReader(f))
    print(f"Existing master_stats_final.csv: {len(existing):,} rows")

    # Load all batch2 CSVs
    new_rows = []
    errors = []
    files = sorted(OUTPUT_DIR.glob("player_*.csv"))
    print(f"Batch2 files found: {len(files)}")

    for fp in files:
        try:
            with open(fp, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Validate columns
                    if not all(c in row for c in FINAL_COLS):
                        continue
                    if row["season"] not in TARGET_SEASONS:
                        continue
                    new_rows.append({c: row[c] for c in FINAL_COLS})
        except Exception as e:
            errors.append((fp.name, str(e)))

    print(f"New rows from batch2: {len(new_rows):,}")
    print(f"Unique new players  : {len({r['tm_id'] for r in new_rows}):,}")

    if errors:
        print(f"\n⚠️  {len(errors)} files had errors:")
        for name, err in errors[:5]:
            print(f"   {name}: {err}")

    # Combine and write
    all_rows = existing + new_rows
    with open(MASTER_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FINAL_COLS)
        writer.writeheader()
        writer.writerows(all_rows)

    print("\n✅ master_stats_final.csv updated")
    print(f"   Total rows     : {len(all_rows):,}")
    print(f"   Unique players : {len({r['tm_id'] for r in all_rows}):,}")
    print(f"   Seasons        : {sorted({r['season'] for r in all_rows})}")


if __name__ == "__main__":
    main()
