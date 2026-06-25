# paste this in a new file debug_excel.py and run it
import openpyxl

wb = openpyxl.load_workbook(
    r"C:\Users\Aarya\Downloads\Pitchguard\pitchguard\src\scrapers\data\raw\player_stats_links1.xlsx",
    read_only=True,
    data_only=True,
)
ws = wb.active

print("First 50 rows of column B (index 1):")
for i, row in enumerate(ws.iter_rows(min_row=1, max_row=50, values_only=True)):
    print(f"  row {i:02d}: {repr(row[1])}")

wb.close()
