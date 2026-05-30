r"""
PitchGuard — Transfermarkt Player Bio Scraper
==============================================
Reads the combined squad Excel file, visits each unique player's
Transfermarkt profile URL and scrapes:
  - Date of birth
  - Age
  - Height (cm)
  - Nationality
  - Second nationality (if any)
  - Position (detailed)
  - Strong foot
  - Current club

Usage:
    python tm_player_bio_scraper.py --input data/raw/squad_data_combined.xlsx --output data/raw/player_bios.csv

Requirements:
    pip install selenium webdriver-manager pandas openpyxl
"""

import argparse
import time
import random
import logging
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bio_scraper")


# ---------------------------------------------------------------------------
# Browser factory
# ---------------------------------------------------------------------------
def build_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    opts.add_argument("--lang=en-GB")
    opts.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        },
    )
    return driver


# ---------------------------------------------------------------------------
# Cookie banner
# ---------------------------------------------------------------------------
def dismiss_cookies(driver: webdriver.Chrome) -> None:
    try:
        btn = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(., 'Agree') or contains(., 'Accept') "
                    "or @id='onetrust-accept-btn-handler']",
                )
            )
        )
        btn.click()
        time.sleep(1)
        log.info("Cookie banner dismissed.")
    except TimeoutException:
        pass


# ---------------------------------------------------------------------------
# Safe text helper
# ---------------------------------------------------------------------------
def safe_text(driver, css: str) -> str:
    try:
        return driver.find_element(By.CSS_SELECTOR, css).text.strip()
    except NoSuchElementException:
        return ""


def safe_attr(driver, css: str, attr: str) -> str:
    try:
        return driver.find_element(By.CSS_SELECTOR, css).get_attribute(attr) or ""
    except NoSuchElementException:
        return ""


# ---------------------------------------------------------------------------
# Scrape a single player profile
# ---------------------------------------------------------------------------
def scrape_player_bio(
    driver: webdriver.Chrome, player_tm_id: str, profile_url: str, player_name: str
) -> dict:
    """
    Visit a Transfermarkt player profile page and extract bio details.
    Returns a dict of scraped fields.
    """
    base = {
        "player_tm_id": player_tm_id,
        "player_name": player_name,
        "profile_url": profile_url,
        "dob": "",
        "age": "",
        "height_cm": "",
        "nationality": "",
        "second_nationality": "",
        "detailed_position": "",
        "strong_foot": "",
        "current_club": "",
        "scrape_status": "ok",
    }

    try:
        driver.get(profile_url)
    except Exception as e:
        log.error(f"  Failed to load {profile_url}: {e}")
        base["scrape_status"] = "load_error"
        return base

    # Dismiss cookies on first real page load
    dismiss_cookies(driver)

    # Wait for the player header to appear
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.info-table"))
        )
    except TimeoutException:
        log.warning(f"  Bio table not found for {player_name} ({player_tm_id})")
        base["scrape_status"] = "timeout"
        return base

    time.sleep(random.uniform(1.5, 3.0))

    # ── Parse the info-table rows ──────────────────────────────────────────
    # TM's bio table is a series of <span class="info-table__content"> pairs
    try:
        rows = driver.find_elements(
            By.CSS_SELECTOR, "div.info-table span.info-table__content"
        )
        # Rows come in label/value pairs
        for i in range(0, len(rows) - 1, 2):
            label = rows[i].text.strip().lower()
            value = rows[i + 1].text.strip()

            if "date of birth" in label or "born" in label:
                base["dob"] = value
            elif "age" in label and not base["age"]:
                base["age"] = value
            elif "height" in label:
                # Convert "1,83 m" or "1.83 m" → 183
                height_raw = value.replace(",", ".").replace(" m", "").strip()
                try:
                    base["height_cm"] = str(int(float(height_raw) * 100))
                except ValueError:
                    base["height_cm"] = value
            elif "citizenship" in label or "nationality" in label:
                if not base["nationality"]:
                    base["nationality"] = value
                else:
                    base["second_nationality"] = value
            elif "position" in label:
                base["detailed_position"] = value
            elif "foot" in label:
                base["strong_foot"] = value
            elif "current club" in label or "club" in label:
                base["current_club"] = value

    except Exception as e:
        log.warning(f"  Error parsing info-table for {player_name}: {e}")
        base["scrape_status"] = "parse_error"

    # ── Fallback: try the header area for DOB if still empty ──────────────
    if not base["dob"]:
        dob_fallback = safe_text(driver, "span[itemprop='birthDate']")
        if dob_fallback:
            base["dob"] = dob_fallback

    # ── Fallback: nationality from flag title ─────────────────────────────
    if not base["nationality"]:
        base["nationality"] = safe_attr(
            driver, "span[itemprop='nationality'] img", "title"
        )

    return base


# ---------------------------------------------------------------------------
# Load Excel / CSV Fallback
# ---------------------------------------------------------------------------
def load_squad_excel(path: str) -> pd.DataFrame:
    try:
        # Try reading as standard Excel workbook
        df = pd.read_excel(path, engine="openpyxl")
    except Exception:
        # Fallback if it's actually a CSV masquerading as an XLSX file
        log.warning(
            "⚠️ Excel format could not be read. Attempting to read as a CSV file instead..."
        )
        df = pd.read_csv(path)

    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    required = {"player_tm_id", "profile_url", "player_name"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"File is missing columns: {missing}. Found: {list(df.columns)}"
        )

    # Drop rows with no profile URL or player ID
    df = df.dropna(subset=["player_tm_id", "profile_url"])
    df["player_tm_id"] = df["player_tm_id"].astype(str).str.strip()
    df["profile_url"] = df["profile_url"].astype(str).str.strip()

    # Deduplicate on player_tm_id — keep first occurrence
    before = len(df)
    df = df.drop_duplicates(subset=["player_tm_id"])
    after = len(df)
    if before != after:
        log.info(f"Removed {before - after} duplicate player IDs.")

    log.info(f"Loaded {len(df)} unique players from {path}.")
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run(
    input_path: str, output_path: str, headless: bool = True, resume: bool = True
) -> None:
    df = load_squad_excel(input_path)

    # ── Resume support: skip already-scraped players ──────────────────────
    already_done: set[str] = set()
    if resume:
        try:
            done_df = pd.read_csv(output_path, dtype=str)
            already_done = set(done_df["player_tm_id"].dropna().tolist())
            log.info(
                f"Resuming — {len(already_done)} players already scraped, skipping them."
            )
        except FileNotFoundError:
            pass

    to_scrape = df[~df["player_tm_id"].isin(already_done)]
    log.info(f"{len(to_scrape)} players to scrape.")

    if to_scrape.empty:
        log.info("Nothing to scrape — all players already done.")
        return

    driver = build_driver(headless=headless)
    results: list[dict] = []

    try:
        for i, (_, row) in enumerate(to_scrape.iterrows(), 1):
            player_tm_id = str(row["player_tm_id"])
            profile_url = str(row["profile_url"])
            player_name = str(row.get("player_name", ""))

            log.info(f"[{i}/{len(to_scrape)}] {player_name} (ID: {player_tm_id})")

            bio = scrape_player_bio(driver, player_tm_id, profile_url, player_name)
            results.append(bio)

            # Save checkpoint every 50 players
            if i % 50 == 0:
                _append_and_save(results, output_path, already_done)
                already_done.update(r["player_tm_id"] for r in results)
                results = []
                log.info(f"  💾 Checkpoint saved at {i} players.")

            # Delay between players: 3–6 seconds
            if i < len(to_scrape):
                time.sleep(random.uniform(3, 6))

    finally:
        driver.quit()
        log.info("Browser closed.")

    # Save any remaining results
    if results:
        _append_and_save(results, output_path, already_done)

    # Final summary
    final_df = pd.read_csv(output_path)
    log.info(f"\n✅ Done. {len(final_df)} player bios saved to {output_path}")
    ok = (final_df["scrape_status"] == "ok").sum()
    fails = len(final_df) - ok
    log.info(f"   Successful: {ok}  |  Failed/timeout: {fails}")


def _append_and_save(
    new_rows: list[dict], output_path: str, already_done: set[str]
) -> None:
    new_df = pd.DataFrame(new_rows)
    try:
        existing = pd.read_csv(output_path, dtype=str)
        combined = pd.concat([existing, new_df], ignore_index=True)
    except FileNotFoundError:
        combined = new_df
    combined.to_csv(output_path, index=False, encoding="utf-8-sig")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape Transfermarkt player bio details from profile URLs."
    )
    parser.add_argument(
        "--input", "-i", required=True, help="Path to combined squad Excel file"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="data/raw/player_bios.csv",
        help="Output CSV path (default: data/raw/player_bios.csv)",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show Chrome window (useful for debugging)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Start fresh, ignore any existing output file",
    )
    args = parser.parse_args()

    run(
        input_path=args.input,
        output_path=args.output,
        headless=not args.no_headless,
        resume=not args.no_resume,
    )
