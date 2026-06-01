"""
PitchGuard — FBref Match Log Scraper
=====================================
Uses Selenium for FBref player search (avoids 403),
and pandas.read_html() for parsing match log tables.

Usage:
    python fbref_matchlog_scraper.py \
        --input data/raw/squad_data_combined.csv \
        --output data/raw/match_logs_raw.csv

Requirements:
    pip install selenium webdriver-manager beautifulsoup4 pandas lxml requests
"""

import argparse
import logging
import time
import random
import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("fbref_scraper")

# ── Constants ─────────────────────────────────────────────────────────────────
SEASONS = [
    "2019-2020", "2020-2021", "2021-2022",
    "2022-2023", "2023-2024", "2024-2025",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

SEARCH_URL   = "https://fbref.com/en/search/search.fcgi?search={}"
MATCHLOG_URL = "https://fbref.com/en/players/{}/matchlogs/{}/summary/"

CHECKPOINT_EVERY = 20
SEARCH_DELAY_MIN = 4.0
SEARCH_DELAY_MAX = 6.0
LOG_DELAY_MIN    = 5.0
LOG_DELAY_MAX    = 8.0


# ── Selenium browser ──────────────────────────────────────────────────────────
def build_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    opts.add_argument("--lang=en-GB")
    opts.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())
    driver  = webdriver.Chrome(service=service, options=opts)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver


def dismiss_cookies(driver: webdriver.Chrome) -> None:
    try:
        btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//button[contains(., 'Agree') or contains(., 'Accept') "
                "or contains(., 'consent')]"
            ))
        )
        btn.click()
        time.sleep(1)
    except TimeoutException:
        pass


# ── FBref search via Selenium ─────────────────────────────────────────────────
def search_fbref(driver: webdriver.Chrome, player_name: str):
    """
    Search FBref for a player using Selenium.
    Returns (fbref_id, slug) or (None, None).
    """
    url = SEARCH_URL.format(player_name.replace(" ", "+"))
    time.sleep(random.uniform(SEARCH_DELAY_MIN, SEARCH_DELAY_MAX))

    try:
        driver.get(url)
    except Exception as e:
        log.warning(f"  Selenium load error for '{player_name}': {e}")
        return None, None

    dismiss_cookies(driver)
    time.sleep(random.uniform(1.5, 2.5))

    current_url = driver.current_url

    # Direct redirect to player page
    if "/en/players/" in current_url and "/search/" not in current_url:
        m      = re.search(r"/en/players/([a-z0-9]+)/", current_url)
        slug_m = re.search(r"/en/players/[a-z0-9]+/([^/?]+)", current_url)
        if m:
            log.info(f"  Direct match: {m.group(1)}")
            return m.group(1), (slug_m.group(1) if slug_m else "")

    # Parse search results from page source
    soup = BeautifulSoup(driver.page_source, "lxml")

    for item in soup.select("div.search-item"):
        link = item.select_one("a")
        if not link:
            continue
        href = link.get("href", "")
        if "/en/players/" not in href:
            continue
        m = re.search(r"/en/players/([a-z0-9]+)/", href)
        if m:
            slug_m = re.search(r"/en/players/[a-z0-9]+/([^/?]+)", href)
            log.info(f"  Search match: {m.group(1)} for '{player_name}'")
            return m.group(1), (slug_m.group(1) if slug_m else "")

    # Also try any player link on the page
    for a in soup.select("a[href*='/en/players/']"):
        href = a.get("href", "")
        m    = re.search(r"/en/players/([a-z0-9]+)/", href)
        if m:
            slug_m = re.search(r"/en/players/[a-z0-9]+/([^/?]+)", href)
            log.info(f"  Fallback match: {m.group(1)} for '{player_name}'")
            return m.group(1), (slug_m.group(1) if slug_m else "")

    log.warning(f"  Not found on FBref: '{player_name}'")
    return None, None


# ── Match log scraping via requests + pandas ──────────────────────────────────
def scrape_season(fbref_id: str, season: str, player_name: str, player_tm_id: str) -> list[dict]:
    url = MATCHLOG_URL.format(fbref_id, season)
    time.sleep(random.uniform(LOG_DELAY_MIN, LOG_DELAY_MAX))

    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
    except Exception as e:
        log.warning(f"    [{season}] Request error: {e}")
        return []

    if resp.status_code == 429:
        log.warning(f"    [{season}] Rate limited — waiting 90s...")
        time.sleep(90)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
        except Exception:
            return []

    if resp.status_code != 200:
        log.warning(f"    [{season}] HTTP {resp.status_code} for {player_name}")
        return []

    if "/en/players/" not in resp.url:
        log.warning(f"    [{season}] Redirected away — skipping")
        return []

    try:
        tables = pd.read_html(resp.text, attrs={"id": re.compile(r"matchlogs")})
    except Exception:
        try:
            tables = pd.read_html(resp.text)
        except Exception:
            log.warning(f"    [{season}] No parseable table for {player_name}")
            return []

    if not tables:
        return []

    df = tables[0].copy()

    # Drop repeated header rows FBref injects
    for date_col in ["Date", "date"]:
        if date_col in df.columns:
            df = df[df[date_col] != date_col].copy()
            break

    df.columns = [str(c).lower().strip() for c in df.columns]

    col_map = {
        "date":     "match_date",
        "comp":     "competition",
        "squad":    "squad",
        "opponent": "opponent",
        "venue":    "home_away",
        "min":      "minutes_played",
    }
    df = df.rename(columns=col_map)
    keep = [c for c in col_map.values() if c in df.columns]
    df   = df[keep].copy()

    df["season"]          = season
    df["fbref_player_id"] = fbref_id
    df["player_name"]     = player_name
    df["player_tm_id"]    = player_tm_id

    if "minutes_played" in df.columns:
        df["minutes_played"] = (
            df["minutes_played"]
            .astype(str)
            .str.replace(",", "")
            .str.extract(r"(\d+)")[0]
        )
        df["minutes_played"] = pd.to_numeric(df["minutes_played"], errors="coerce")

    if "match_date" in df.columns:
        df = df[df["match_date"].notna() & (df["match_date"].astype(str).str.strip() != "")]

    rows = df.to_dict(orient="records")
    log.info(f"    [{season}] ✓ {len(rows)} appearances for {player_name}")
    return rows


# ── Crosswalk helpers ─────────────────────────────────────────────────────────
def load_crosswalk(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    df = pd.read_csv(p, dtype=str).fillna("")
    result = {}
    for _, row in df.iterrows():
        result[str(row["player_tm_id"])] = (
            row.get("player_name", ""),
            row.get("fbref_player_id", ""),
            row.get("fbref_slug", ""),
        )
    log.info(f"Loaded {len(result)} crosswalk entries.")
    return result


def save_crosswalk(crosswalk: dict, path: str) -> None:
    rows = [
        {
            "player_tm_id":    tm_id,
            "player_name":     v[0],
            "fbref_player_id": v[1],
            "fbref_slug":      v[2],
        }
        for tm_id, v in crosswalk.items()
    ]
    pd.DataFrame(rows).to_csv(path, index=False)


def _append_to_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        return
    df = pd.DataFrame(rows)
    if path.exists():
        df.to_csv(path, mode="a", header=False, index=False)
    else:
        df.to_csv(path, index=False)


# ── Main ──────────────────────────────────────────────────────────────────────
def run(input_path: str, output_path: str) -> None:
    p        = Path(input_path)
    squad_df = pd.read_excel(p, dtype=str) if p.suffix in (".xlsx", ".xls") else pd.read_csv(p, dtype=str)
    squad_df = squad_df.fillna("")

    required = {"player_name", "player_tm_id"}
    missing  = required - set(squad_df.columns)
    if missing:
        raise ValueError(f"Input missing columns: {missing}")

    before   = len(squad_df)
    squad_df = squad_df.drop_duplicates(subset=["player_tm_id"])
    log.info(f"Loaded {len(squad_df)} unique players ({before - len(squad_df)} duplicates removed)")

    out_path       = Path(output_path)
    crosswalk_path = str(out_path.parent / "fbref_crosswalk.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Resume support
    already_done: set[str] = set()
    if out_path.exists():
        existing     = pd.read_csv(out_path, dtype=str)
        already_done = set(existing["player_tm_id"].dropna().unique())
        log.info(f"Resuming — {len(already_done)} players already scraped, skipping.")

    crosswalk = load_crosswalk(crosswalk_path)

    log.info("Starting Chrome for FBref search...")
    driver = build_driver()

    all_rows:  list[dict] = []
    processed: int        = 0
    total = len(squad_df)

    try:
        for i, player in enumerate(squad_df.itertuples(), 1):
            tm_id       = str(player.player_tm_id).strip()
            player_name = str(player.player_name).strip()

            log.info(f"[{i}/{total}] {player_name} (tm_id={tm_id})")

            if tm_id in already_done:
                log.info("  Already scraped — skipping.")
                continue

            # Get FBref ID from cache or search
            if tm_id in crosswalk and crosswalk[tm_id][1]:
                _, fbref_id, slug = crosswalk[tm_id]
                log.info(f"  FBref ID from cache: {fbref_id}")
            else:
                fbref_id, slug = search_fbref(driver, player_name)
                crosswalk[tm_id] = (player_name, fbref_id or "", slug or "")
                save_crosswalk(crosswalk, crosswalk_path)

            if not fbref_id:
                log.warning(f"  Skipping {player_name} — no FBref ID found.")
                continue

            # Scrape all seasons
            player_rows: list[dict] = []
            for season in SEASONS:
                rows = scrape_season(fbref_id, season, player_name, tm_id)
                player_rows.extend(rows)

            log.info(f"  Total: {len(player_rows)} appearances across all seasons")
            all_rows.extend(player_rows)
            processed += 1

            if processed % CHECKPOINT_EVERY == 0:
                _append_to_csv(all_rows, out_path)
                all_rows = []
                log.info(f"  💾 Checkpoint saved at player {i}/{total}")

    finally:
        driver.quit()
        log.info("Browser closed.")

    if all_rows:
        _append_to_csv(all_rows, out_path)

    save_crosswalk(crosswalk, crosswalk_path)

    log.info("\n✅ Done.")
    log.info(f"   Match logs → {out_path}")
    log.info(f"   Crosswalk  → {crosswalk_path}")

    if out_path.exists():
        final_df = pd.read_csv(out_path)
        log.info(f"   Total rows : {len(final_df)}")
        log.info(f"   Players    : {final_df['player_name'].nunique()}")
        log.info(f"   Seasons    : {sorted(final_df['season'].unique())}")


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape FBref match logs for PitchGuard")
    parser.add_argument("--input",  "-i", default="data/raw/squad_data_combined.csv")
    parser.add_argument("--output", "-o", default="data/raw/match_logs_raw.csv")
    args = parser.parse_args()
    run(args.input, args.output)