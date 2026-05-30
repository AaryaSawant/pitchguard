"""
PitchGuard — Transfermarkt Squad Scraper
=========================================
Reads a list of clubs from an Excel file (column: "club_name") and scrapes
every player in that club's current squad from Transfermarkt.

Usage:
    python tm_squad_scraper.py --input clubs.xlsx --output squad_data.csv

Requirements:
    pip install selenium pandas openpyxl webdriver-manager
"""

import argparse
import time
import random
import re
import logging
import pandas as pd

from dataclasses import dataclass

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("tm_scraper")


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------
@dataclass
class PlayerRow:
    club_name: str
    club_tm_id: str
    player_name: str
    player_tm_id: str
    position: str
    nationality: str
    age: str
    market_value: str
    shirt_number: str
    profile_url: str


# ---------------------------------------------------------------------------
# Transfermarkt club name → URL slug + numeric ID lookup
# This maps every one of the 100 clubs to their exact TM URL.
# Format:  "Club Name": ("url-slug", "numeric_tm_id")
# ---------------------------------------------------------------------------
CLUB_LOOKUP: dict[str, tuple[str, str]] = {
    # Premier League
    "Arsenal": ("fc-arsenal", "11"),
    "Aston Villa": ("aston-villa", "405"),
    "Brentford": ("brentford-fc", "1148"),
    "Brighton & Hove Albion": ("brighton-hove-albion", "1237"),
    "Chelsea": ("fc-chelsea", "631"),
    "Crystal Palace": ("crystal-palace", "873"),
    "Everton": ("fc-everton", "29"),
    "Fulham": ("fc-fulham", "931"),
    "Ipswich Town": ("ipswich-town", "677"),
    "Leicester City": ("leicester-city", "1003"),
    "Liverpool": ("fc-liverpool", "31"),
    "Manchester City": ("manchester-city", "281"),
    "Manchester United": ("manchester-united", "985"),
    "Newcastle United": ("newcastle-united", "762"),
    "Nottingham Forest": ("nottingham-forest", "703"),
    "Southampton": ("fc-southampton", "180"),
    "Tottenham Hotspur": ("tottenham-hotspur", "148"),
    "West Ham United": ("west-ham-united", "379"),
    "Wolverhampton Wanderers": ("wolverhampton-wanderers", "543"),
    "Bournemouth": ("afc-bournemouth", "989"),
    # La Liga
    "Real Madrid": ("real-madrid", "418"),
    "FC Barcelona": ("fc-barcelona", "131"),
    "Atletico Madrid": ("atletico-de-madrid", "13"),
    "Sevilla FC": ("fc-sevilla", "368"),
    "Real Betis": ("real-betis-balompie", "150"),
    "Real Sociedad": ("real-sociedad", "681"),
    "Athletic Bilbao": ("athletic-club", "621"),
    "Villarreal CF": ("villarreal-cf", "383"),
    "Valencia CF": ("fc-valencia", "1049"),
    "Celta Vigo": ("rc-celta-de-vigo", "940"),
    "Rayo Vallecano": ("rayo-vallecano", "367"),
    "Osasuna": ("ca-osasuna", "331"),
    "Getafe CF": ("getafe-cf", "3709"),
    "Girona FC": ("girona-fc", "12321"),
    "UD Las Palmas": ("ud-las-palmas", "472"),
    "Deportivo Alaves": ("deportivo-alaves", "1108"),
    "RCD Mallorca": ("rcd-mallorca", "237"),
    "CD Leganes": ("cd-leganes", "5905"),
    "Real Valladolid": ("real-valladolid-cf", "366"),
    "Espanyol": ("rcd-espanyol-barcelona", "714"),
    # Bundesliga
    "Bayern Munich": ("fc-bayern-munchen", "27"),
    "Borussia Dortmund": ("borussia-dortmund", "16"),
    "Bayer Leverkusen": ("bayer-04-leverkusen", "15"),
    "RB Leipzig": ("rasenballsport-leipzig", "23826"),
    "Eintracht Frankfurt": ("eintracht-frankfurt", "24"),
    "VfB Stuttgart": ("vfb-stuttgart", "79"),
    "Werder Bremen": ("sv-werder-bremen", "86"),
    "SC Freiburg": ("sport-club-freiburg", "60"),
    "TSG Hoffenheim": ("tsg-1899-hoffenheim", "533"),
    "Borussia Monchengladbach": ("borussia-monchengladbach", "23"),
    "FC Augsburg": ("fc-augsburg", "167"),
    "1. FC Union Berlin": ("1-fc-union-berlin", "89"),
    "VfL Bochum": ("vfl-bochum", "80"),
    "SV Darmstadt 98": ("sv-darmstadt-98", "105"),
    "1. FC Heidenheim": ("1-fc-heidenheim-1846", "2036"),
    "Holstein Kiel": ("holstein-kiel", "4372"),
    "FC St. Pauli": ("fc-st-pauli", "35"),
    "VfL Wolfsburg": ("vfl-wolfsburg", "82"),
    # Serie A
    "Inter Milan": ("inter-mailand", "46"),
    "AC Milan": ("ac-mailand", "5"),
    "Juventus": ("juventus-turin", "506"),
    "AS Roma": ("as-rom", "12"),
    "SSC Napoli": ("ssc-neapel", "6195"),
    "Lazio": ("lazio-rom", "398"),
    "Atalanta": ("atalanta-bergamo", "800"),
    "Fiorentina": ("acf-fiorentina", "430"),
    "Torino": ("fc-turin", "416"),
    "Bologna": ("fc-bologna", "1025"),
    "Genoa": ("genua-cfc", "252"),
    "Cagliari": ("cagliari-calcio", "1390"),
    "Hellas Verona": ("hellas-verona", "276"),
    "Monza": ("ac-monza", "9462"),
    "Udinese": ("udinese-calcio", "410"),
    "Como": ("como-1907", "2324"),
    "Venezia": ("fc-venedig", "685"),
    "Parma": ("parma-calcio-1913", "130"),
    "Empoli": ("fc-empoli", "749"),
    "Lecce": ("us-lecce", "4884"),
    # Ligue 1
    "Paris Saint-Germain": ("paris-saint-germain", "583"),
    "Olympique de Marseille": ("olympique-marseille", "244"),
    "Olympique Lyonnais": ("olympique-lyon", "1041"),
    "AS Monaco": ("as-monaco", "162"),
    "Lille OSC": ("losc-lille", "1082"),
    "OGC Nice": ("ogc-nizza", "417"),
    "Stade Rennais": ("stade-rennais", "273"),
    "RC Lens": ("rc-lens", "826"),
    "Montpellier HSC": ("montpellier-hsc", "969"),
    "Strasbourg": ("rc-strasbourg-alsace", "667"),
    "FC Nantes": ("fc-nantes", "995"),
    "Toulouse FC": ("toulouse-fc", "415"),
    "Stade Brestois": ("stade-brestois-29", "3911"),
    "Angers SCO": ("angers-sco", "1023"),
    "Le Havre AC": ("le-havre-ac", "738"),
    "Auxerre": ("aj-auxerre", "69"),
    "Saint-Etienne": ("as-saint-etienne", "618"),
    "Girondins Bordeaux": ("fc-girondins-bordeaux", "374"),
    # Super Lig
    "Galatasaray": ("galatasaray-sk", "141"),
    "Fenerbahce": ("fenerbahce-sk", "36"),
    "Besiktas": ("besiktas-jk", "114"),
    "Trabzonspor": ("trabzonspor", "449"),
}


# ---------------------------------------------------------------------------
# Browser factory
# ---------------------------------------------------------------------------
def build_driver(headless: bool = True) -> webdriver.Chrome:
    """Create a Chrome WebDriver with anti-detection settings."""
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

    # Patch navigator.webdriver to avoid detection
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        },
    )
    return driver


# ---------------------------------------------------------------------------
# Cookie banner dismissal
# ---------------------------------------------------------------------------
def dismiss_cookies(driver: webdriver.Chrome) -> None:
    """Click the TM cookie consent button if it appears."""
    try:
        btn = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(., 'Agree') or contains(., 'Accept') or @id='onetrust-accept-btn-handler']",
                )
            )
        )
        btn.click()
        time.sleep(1)
        log.info("Cookie banner dismissed.")
    except TimeoutException:
        pass  # No cookie banner — fine


# ---------------------------------------------------------------------------
# Core scraping function: one club
# ---------------------------------------------------------------------------
def scrape_club_squad(
    driver: webdriver.Chrome,
    club_name: str,
    tm_slug: str,
    tm_id: str,
) -> list[PlayerRow]:
    """
    Navigate to a Transfermarkt squad page and extract all players.
    Returns a list of PlayerRow objects.
    """
    url = f"https://www.transfermarkt.co.in/{tm_slug}/startseite/verein/{tm_id}"
    log.info(f"  → {club_name}  |  {url}")

    try:
        driver.get(url)
    except Exception as e:
        log.error(f"Failed to load page for {club_name}: {e}")
        return []

    # Dismiss cookies on first load
    dismiss_cookies(driver)

    # Wait for the squad table to appear
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.items"))
        )
    except TimeoutException:
        log.warning(f"  Squad table not found for {club_name} — skipping.")
        return []

    # Small random delay to mimic human reading
    time.sleep(random.uniform(2.5, 4.5))

    rows: list[PlayerRow] = []

    try:
        table_rows = driver.find_elements(By.CSS_SELECTOR, "table.items tbody tr")
    except NoSuchElementException:
        log.warning(f"  No table rows found for {club_name}.")
        return []

    for tr in table_rows:
        # Skip header / section-divider rows (they have no player link)
        try:
            player_link_el = tr.find_element(By.CSS_SELECTOR, "td.hauptlink a")
        except NoSuchElementException:
            continue

        player_name = player_link_el.text.strip()
        profile_url = player_link_el.get_attribute("href") or ""

        # Extract numeric player TM ID from the profile URL
        tm_player_id = ""
        match = re.search(r"/spieler/(\d+)", profile_url)
        if match:
            tm_player_id = match.group(1)

        # Position
        position = _safe_text(tr, "td.posrela table.inline-table tr:last-child td")

        # Nationality (title attr of first flag image)
        nationality = ""
        try:
            flag = tr.find_element(By.CSS_SELECTOR, "td.zentriert img.flaggenrahmen")
            nationality = flag.get_attribute("title") or ""
        except NoSuchElementException:
            pass

        # Age
        age = _safe_text(tr, "td.zentriert:nth-of-type(3)")

        # Market value
        market_value = _safe_text(tr, "td.rechts.hauptlink")

        # Shirt number
        shirt_number = _safe_text(tr, "div.rn_nummer")

        if not player_name:
            continue

        rows.append(
            PlayerRow(
                club_name=club_name,
                club_tm_id=tm_id,
                player_name=player_name,
                player_tm_id=tm_player_id,
                position=position,
                nationality=nationality,
                age=age,
                market_value=market_value,
                shirt_number=shirt_number,
                profile_url=profile_url,
            )
        )

    log.info(f"  ✓ {len(rows)} players scraped for {club_name}.")
    return rows


def _safe_text(parent, css_selector: str) -> str:
    """Return .text of the first matching element, or empty string."""
    try:
        return parent.find_element(By.CSS_SELECTOR, css_selector).text.strip()
    except NoSuchElementException:
        return ""


# ---------------------------------------------------------------------------
# Excel reader
# ---------------------------------------------------------------------------
def load_clubs_from_excel(path: str) -> list[str]:
    """
    Read the Excel file and return a list of club names.
    Expects a column named exactly 'club_name' (case-insensitive).
    """
    df = pd.read_excel(path)
    df.columns = [c.strip().lower() for c in df.columns]

    if "club_name" not in df.columns:
        raise ValueError(
            f"Excel file must have a column named 'club_name'. "
            f"Found columns: {list(df.columns)}"
        )

    clubs = df["club_name"].dropna().str.strip().tolist()
    log.info(f"Loaded {len(clubs)} clubs from {path}.")
    return clubs


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------
def run(input_path: str, output_path: str, headless: bool = True) -> None:
    club_names = load_clubs_from_excel(input_path)

    # Match club names from Excel to our lookup table (case-insensitive)
    lookup_lower = {k.lower(): (k, v) for k, v in CLUB_LOOKUP.items()}

    matched: list[tuple[str, str, str]] = []  # (club_name, slug, tm_id)
    unmatched: list[str] = []

    for name in club_names:
        key = name.lower()
        if key in lookup_lower:
            original_key, (slug, tm_id) = lookup_lower[key]
            matched.append((name, slug, tm_id))
        else:
            unmatched.append(name)

    if unmatched:
        log.warning(
            f"The following {len(unmatched)} club(s) were NOT found in the lookup table "
            f"and will be skipped:\n  " + "\n  ".join(unmatched)
        )

    if not matched:
        log.error(
            "No clubs matched. Check that your Excel column is named 'club_name' "
            "and club names match the expected names."
        )
        return

    log.info(f"Starting scrape for {len(matched)} clubs...")

    driver = build_driver(headless=headless)
    all_rows: list[PlayerRow] = []

    try:
        for i, (club_name, slug, tm_id) in enumerate(matched, 1):
            log.info(f"[{i}/{len(matched)}] Scraping {club_name}...")
            rows = scrape_club_squad(driver, club_name, slug, tm_id)
            all_rows.extend(rows)

            # Save a checkpoint CSV after every 10 clubs
            if i % 10 == 0:
                _save_csv(all_rows, output_path, checkpoint=True)
                log.info(f"  💾 Checkpoint saved ({len(all_rows)} total rows so far).")

            # Inter-club delay: 5–9 seconds
            if i < len(matched):
                delay = random.uniform(5, 9)
                log.info(f"  Waiting {delay:.1f}s before next club...")
                time.sleep(delay)

    finally:
        driver.quit()
        log.info("Browser closed.")

    _save_csv(all_rows, output_path, checkpoint=False)
    log.info(f"\n✅ Done. {len(all_rows)} players saved to {output_path}")

    # Print summary
    summary = pd.DataFrame(
        all_rows.__iter__() if False else [vars(r) for r in all_rows]
    )
    if not summary.empty:
        counts = summary.groupby("club_name")["player_name"].count().reset_index()
        counts.columns = ["club_name", "player_count"]
        log.info("\nPlayers per club:\n" + counts.to_string(index=False))


def _save_csv(rows: list[PlayerRow], path: str, checkpoint: bool) -> None:
    if not rows:
        return
    save_path = path if not checkpoint else path.replace(".csv", "_checkpoint.csv")
    df = pd.DataFrame([vars(r) for r in rows])
    df.to_csv(save_path, index=False, encoding="utf-8-sig")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape Transfermarkt squad data for clubs listed in an Excel file."
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to Excel file with a 'club_name' column (e.g. clubs.xlsx)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="squad_data.csv",
        help="Output CSV path (default: squad_data.csv)",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run Chrome in visible mode (useful for debugging)",
    )
    args = parser.parse_args()

    run(
        input_path=args.input,
        output_path=args.output,
        headless=not args.no_headless,
    )
