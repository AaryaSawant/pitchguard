"""
PitchGuard — Transfermarkt Player Stats Scraper
================================================
Reads body.innerText directly — no table selectors needed.
TM renders stats via Svelte so there are no real <table> elements.

The innerText block we parse looks like:
    Championship
    46
    38
    16
    -
    -
    -
    4,140'
    Championship Play-Offs
    3
    4
    ...
    Total:
    49
    ...

Output columns:
    player_tm_id, player_name, season, competition, appearances, minutes_played

Usage:
    python tm_player_stats_scraper.py \
        --input  data/raw/player_bios.csv \
        --output data/raw/player_season_stats.csv
"""

import argparse
import logging
import time
import random
import re
from pathlib import Path

import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("tm_stats")

# ── Constants ─────────────────────────────────────────────────────────────────
SEASON_YEARS     = [2019, 2020, 2021, 2022, 2023, 2024]
BASE_URL         = ("https://www.transfermarkt.co.in/{slug}/leistungsdaten"
                    "/spieler/{tm_id}/saison/{year}/plus/1")
CHECKPOINT_EVERY = 30
DELAY_MIN        = 6.0
DELAY_MAX        = 10.0
SEASON_DELAY     = 5.0
PLAYER_DELAY     = 8.0

# Lines that signal end of the stats block
STOP_WORDS = {"total:", "total", "compact", "detailed", "matchday",
              "date", "venue", "home team", "away team"}

# Value line patterns
MINUTES_RE = re.compile(r"^[\d,]+'$")       # e.g. 4,140'
NUMERIC_RE = re.compile(r"^[\d,]+$")        # e.g. 46
DASH_RE    = re.compile(r"^-+$")            # e.g. -


# ── Browser ───────────────────────────────────────────────────────────────────
def build_driver() -> uc.Chrome:
    opts = uc.ChromeOptions()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--lang=en-GB")
    driver = uc.Chrome(options=opts, version_main=148)
    driver.set_window_size(1400, 900)
    return driver


def dismiss_cookies(driver: uc.Chrome) -> None:
    try:
        btn = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//button[contains(.,'Agree') or contains(.,'Accept') "
                "or contains(.,'Consent') or @id='onetrust-accept-btn-handler']"
            ))
        )
        btn.click()
        time.sleep(1.5)
        log.info("Cookie banner dismissed.")
    except TimeoutException:
        pass


# ── Core parser ───────────────────────────────────────────────────────────────
def parse_innertext(text: str, player_tm_id: str,
                    player_name: str, season_label: str) -> list[dict]:
    """
    Parse body.innerText of a TM stats page.
    Finds the 'STATS OF' section, then walks line by line consuming
    competition name + 7 value lines per block.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # Find anchor: "STATS OF ..."
    start = None
    for i, line in enumerate(lines):
        if "stats of" in line.lower():
            start = i
            break

    if start is None:
        return []

    rows = []
    i = start + 1
    current_comp = None
    values_buf: list[str] = []

    def is_value(s: str) -> bool:
        return bool(MINUTES_RE.match(s) or NUMERIC_RE.match(s) or DASH_RE.match(s))

    def flush(comp: str, buf: list[str]):
        if not comp or not buf:
            return None
        # appearances = first value token that is numeric (not dash)
        appearances = ""
        for v in buf:
            if NUMERIC_RE.match(v):
                appearances = v.replace(",", "")
                break
        # minutes = token ending in '
        minutes = ""
        for v in buf:
            if MINUTES_RE.match(v):
                minutes = v.replace("'", "").replace(",", "")
                break
        # skip rows with no real data
        if not appearances and not minutes:
            return None
        return {
            "player_tm_id":   player_tm_id,
            "player_name":    player_name,
            "season":         season_label,
            "competition":    comp,
            "appearances":    appearances or "0",
            "minutes_played": minutes or "",
        }

    while i < len(lines):
        line = lines[i]

        # Stop at Total row
        if line.lower().startswith("total"):
            if current_comp and values_buf:
                r = flush(current_comp, values_buf)
                if r:
                    rows.append(r)
            break

        # Skip UI chrome
        if line.lower() in STOP_WORDS or line.lower().startswith("filter"):
            i += 1
            continue

        if is_value(line):
            values_buf.append(line)
            # Each competition block has 7 value lines
            if len(values_buf) >= 7:
                if current_comp:
                    r = flush(current_comp, values_buf)
                    if r:
                        rows.append(r)
                current_comp = None
                values_buf   = []
        else:
            # New competition name — flush previous
            if current_comp and values_buf:
                r = flush(current_comp, values_buf)
                if r:
                    rows.append(r)
            current_comp = line
            values_buf   = []

        i += 1

    return rows


# ── Scrape one season ─────────────────────────────────────────────────────────
def scrape_season(driver: uc.Chrome, player_tm_id: str,
                   player_name: str, season_year: int) -> list[dict]:
    season_label = f"{season_year}/{str(season_year + 1)[-2:]}"

    # Wait for body
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
    except TimeoutException:
        log.warning(f"      Timeout loading page for {player_name} {season_label}")
        return []

    # Poll until "stats of" appears in innerText (max 25s)
    # Poll until "stats of" appears in innerText (max 25s)
    text = ""
    for _ in range(25):
        try:
            text = driver.execute_script("return document.body.innerText;") or ""
            if "stats of" in text.lower():
                break
        except Exception:
            pass
        time.sleep(1)

    if "stats of" not in text.lower():
        log.warning("      Stats content never appeared — waiting 30s and retrying...")
        time.sleep(30)
        text = driver.execute_script("return document.body.innerText;") or ""
        if "stats of" not in text.lower():
            log.warning(f"      Giving up on {player_name} {season_label}")
            return []
    # Cloudflare check
    if "just a moment" in (driver.title or "").lower():
        log.warning(f"      Cloudflare block for {player_name} {season_label} — waiting 30s")
        time.sleep(30)
        text = driver.execute_script("return document.body.innerText;") or ""

    rows = parse_innertext(text, player_tm_id, player_name, season_label)
    log.info(f"      ✓ {len(rows)} competition rows for {season_label}")
    return rows


# ── Scrape one player ─────────────────────────────────────────────────────────
def scrape_player(driver: uc.Chrome, player_tm_id: str,
                   player_name: str, slug: str,
                   cookies_dismissed: list) -> list[dict]:
    all_rows = []
    for year in SEASON_YEARS:
        url = BASE_URL.format(slug=slug, tm_id=player_tm_id, year=year)
        log.info(f"    Season {year}/{str(year + 1)[-2:]}")
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

        try:
            driver.get(url)
        except Exception as e:
            log.warning(f"    Load error: {e}")
            continue

        if not cookies_dismissed[0]:
            dismiss_cookies(driver)
            cookies_dismissed[0] = True

        rows = scrape_season(driver, player_tm_id, player_name, year)
        all_rows.extend(rows)
        time.sleep(SEASON_DELAY)

    return all_rows


# ── Helpers ───────────────────────────────────────────────────────────────────
def extract_slug(profile_url: str) -> str:
    m = re.search(r"transfermarkt\.[a-z.]+/([^/]+)/profil", profile_url or "")
    return m.group(1) if m else ""


def load_input(path: str) -> pd.DataFrame:
    p  = Path(path)
    df = pd.read_excel(p, dtype=str) if p.suffix in (".xlsx", ".xls") else pd.read_csv(p, dtype=str)
    df = df.fillna("")
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    missing = {"player_tm_id", "profile_url", "player_name"} - set(df.columns)
    if missing:
        raise ValueError(f"Input missing columns: {missing}")
    before = len(df)
    df = df.drop_duplicates(subset=["player_tm_id"])
    log.info(f"Loaded {len(df)} unique players ({before - len(df)} dupes removed).")
    return df


def append_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        return
    pd.DataFrame(rows).to_csv(
        path,
        mode="a" if path.exists() else "w",
        header=not path.exists(),
        index=False,
        encoding="utf-8-sig",
    )


# ── Main ──────────────────────────────────────────────────────────────────────
def run(input_path: str, output_path: str) -> None:
    df  = load_input(input_path)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Resume support
    done: set[str] = set()
    if out.exists():
        done = set(pd.read_csv(out, dtype=str)["player_tm_id"].dropna().unique())
        log.info(f"Resuming — {len(done)} players already done, skipping.")

    to_do = df[~df["player_tm_id"].isin(done)]
    log.info(f"{len(to_do)} players left to scrape.")

    if to_do.empty:
        log.info("All done!")
        return

    driver = build_driver()
    cookies_dismissed = [False]
    buffer: list[dict] = []
    total = len(to_do)

    try:
        for i, (_, row) in enumerate(to_do.iterrows(), 1):
            tm_id = str(row["player_tm_id"]).strip()
            name  = str(row["player_name"]).strip()
            slug  = extract_slug(str(row["profile_url"]))

            if not slug:
                log.warning(f"[{i}/{total}] No slug for {name} — skipping.")
                continue

            log.info(f"[{i}/{total}] {name}  (slug={slug}, tm_id={tm_id})")

            rows = scrape_player(driver, tm_id, name, slug, cookies_dismissed)
            buffer.extend(rows)
            log.info(f"  → {len(rows)} total rows for {name}")
            time.sleep(PLAYER_DELAY)

            if i % CHECKPOINT_EVERY == 0:
                append_csv(buffer, out)
                buffer = []
                log.info(f"  💾 Checkpoint saved at {i}/{total}")

    except KeyboardInterrupt:
        log.info("\n⚠️  Ctrl+C — saving progress before exit...")
    finally:
        append_csv(buffer, out)
        try:
            driver.quit()
        except Exception:
            pass
        log.info("Browser closed.")

    if out.exists():
        final = pd.read_csv(out)
        log.info(f"\n✅ Done. {len(final)} rows saved → {out}")
        log.info(f"   Players : {final['player_tm_id'].nunique()}")
        log.info(f"   Seasons : {sorted(final['season'].unique())}")


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--input",  "-i", default="data/raw/player_bios.csv")
    p.add_argument("--output", "-o", default="data/raw/player_season_stats.csv")
    args = p.parse_args()
    run(args.input, args.output)