"""
PitchGuard — Transfermarkt Injury History Scraper
==================================================
Reads squad_data.csv (output of tm_squad_scraper.py) and scrapes the full
injury history for every player from their Transfermarkt profile.

Columns in output CSV:
    player_name, player_tm_id, current_club, season, injury_type,
    injury_date, return_date, games_missed, opponent_club, opponent_mapped

opponent_mapped:
  - Exact club name from our 100-club list  (if opponent is in the list)
  - "Unspecified"                            (if opponent is NOT in the list)
  - ""                                       (if no opponent data on TM)

Usage:
    python tm_injury_scraper.py --input data/raw/squad_data.csv \
                                --output data/raw/injury_data.csv

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
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("tm_injury_scraper")


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------
@dataclass
class InjuryRow:
    player_name: str
    player_tm_id: str
    current_club: str
    season: str
    injury_type: str
    injury_date: str
    return_date: str
    games_missed: str
    opponent_club: str  # Raw text from Transfermarkt
    opponent_mapped: str  # Mapped to our 100-club list or "Unspecified"


# ---------------------------------------------------------------------------
# 100-club list — exact same as tm_squad_scraper.py
# Used for fuzzy-matching the opponent column
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

# Build a lowercase set for fast opponent matching
# Also include common TM alternate spellings
CLUB_NAMES_LOWER: dict[str, str] = {k.lower(): k for k in CLUB_LOOKUP}

# Common alternate names TM uses (German spellings, abbreviations etc.)
CLUB_ALIASES: dict[str, str] = {
    "fc barcelona": "FC Barcelona",
    "barcelona": "FC Barcelona",
    "real madrid cf": "Real Madrid",
    "atletico madrid": "Atletico Madrid",
    "atlético de madrid": "Atletico Madrid",
    "inter mailand": "Inter Milan",
    "inter": "Inter Milan",
    "ac mailand": "AC Milan",
    "milan": "AC Milan",
    "juventus turin": "Juventus",
    "juventus": "Juventus",
    "as rom": "AS Roma",
    "ssc neapel": "SSC Napoli",
    "napoli": "SSC Napoli",
    "fc bayern münchen": "Bayern Munich",
    "fc bayern munchen": "Bayern Munich",
    "bayern": "Bayern Munich",
    "borussia dortmund": "Borussia Dortmund",
    "bvb": "Borussia Dortmund",
    "paris saint-germain": "Paris Saint-Germain",
    "psg": "Paris Saint-Germain",
    "olympique marseille": "Olympique de Marseille",
    "marseille": "Olympique de Marseille",
    "olympique lyonnais": "Olympique Lyonnais",
    "lyon": "Olympique Lyonnais",
    "tottenham": "Tottenham Hotspur",
    "spurs": "Tottenham Hotspur",
    "man city": "Manchester City",
    "man utd": "Manchester United",
    "manchester utd": "Manchester United",
    "newcastle": "Newcastle United",
    "wolves": "Wolverhampton Wanderers",
    "west ham": "West Ham United",
    "fenerbahçe": "Fenerbahce",
    "beşiktaş": "Besiktas",
    "galatasaray sk": "Galatasaray",
    "genua cfc": "Genoa",
    "fc venedig": "Venezia",
    "fc turin": "Torino",
    "lazio rom": "Lazio",
    "as saint-etienne": "Saint-Etienne",
    "girondins bordeaux": "Girondins Bordeaux",
    "rc strasbourg alsace": "Strasbourg",
    "losc lille": "Lille OSC",
    "lille": "Lille OSC",
    "ogc nizza": "OGC Nice",
    "nice": "OGC Nice",
    "stade rennais": "Stade Rennais",
    "rennes": "Stade Rennais",
    "stade brestois 29": "Stade Brestois",
    "brest": "Stade Brestois",
    "aj auxerre": "Auxerre",
    "tsg 1899 hoffenheim": "TSG Hoffenheim",
    "hoffenheim": "TSG Hoffenheim",
    "sport-club freiburg": "SC Freiburg",
    "freiburg": "SC Freiburg",
    "sv werder bremen": "Werder Bremen",
    "werder": "Werder Bremen",
    "rasenballsport leipzig": "RB Leipzig",
    "rb leipzig": "RB Leipzig",
    "eintracht frankfurt": "Eintracht Frankfurt",
    "frankfurt": "Eintracht Frankfurt",
    "vfb stuttgart": "VfB Stuttgart",
    "stuttgart": "VfB Stuttgart",
    "borussia mönchengladbach": "Borussia Monchengladbach",
    "gladbach": "Borussia Monchengladbach",
    "1. fc union berlin": "1. FC Union Berlin",
    "union berlin": "1. FC Union Berlin",
    "vfl bochum": "VfL Bochum",
    "sv darmstadt 98": "SV Darmstadt 98",
    "darmstadt": "SV Darmstadt 98",
    "1. fc heidenheim 1846": "1. FC Heidenheim",
    "heidenheim": "1. FC Heidenheim",
    "fc st. pauli": "FC St. Pauli",
    "st. pauli": "FC St. Pauli",
    "vfl wolfsburg": "VfL Wolfsburg",
    "wolfsburg": "VfL Wolfsburg",
    "fc augsburg": "FC Augsburg",
    "augsburg": "FC Augsburg",
    "hellas verona": "Hellas Verona",
    "verona": "Hellas Verona",
    "udinese calcio": "Udinese",
    "cagliari calcio": "Cagliari",
    "acf fiorentina": "Fiorentina",
    "fc bologna": "Bologna",
    "atalanta bergamo": "Atalanta",
    "como 1907": "Como",
    "parma calcio 1913": "Parma",
    "fc empoli": "Empoli",
    "us lecce": "Lecce",
    "ac monza": "Monza",
    "genua": "Genoa",
    "brighton": "Brighton & Hove Albion",
    "brighton & hove albion": "Brighton & Hove Albion",
    "nottingham forest": "Nottingham Forest",
    "forest": "Nottingham Forest",
    "afc bournemouth": "Bournemouth",
    "leicester": "Leicester City",
    "ipswich": "Ipswich Town",
    "crystal palace": "Crystal Palace",
    "aston villa": "Aston Villa",
    "brentford fc": "Brentford",
    "fc chelsea": "Chelsea",
    "fc everton": "Everton",
    "fc fulham": "Fulham",
    "fc liverpool": "Liverpool",
    "fc southampton": "Southampton",
    "villarreal": "Villarreal CF",
    "real betis": "Real Betis",
    "real sociedad": "Real Sociedad",
    "athletic club": "Athletic Bilbao",
    "athletic bilbao": "Athletic Bilbao",
    "celta vigo": "Celta Vigo",
    "rc celta de vigo": "Celta Vigo",
    "rayo vallecano": "Rayo Vallecano",
    "ca osasuna": "Osasuna",
    "getafe": "Getafe CF",
    "girona": "Girona FC",
    "las palmas": "UD Las Palmas",
    "alaves": "Deportivo Alaves",
    "deportivo alaves": "Deportivo Alaves",
    "mallorca": "RCD Mallorca",
    "rcd mallorca": "RCD Mallorca",
    "leganes": "CD Leganes",
    "valladolid": "Real Valladolid",
    "espanyol": "Espanyol",
    "rcd espanyol": "Espanyol",
    "sevilla": "Sevilla FC",
    "fc sevilla": "Sevilla FC",
    "valencia": "Valencia CF",
    "fc valencia": "Valencia CF",
    "trabzonspor": "Trabzonspor",
    "besiktas jk": "Besiktas",
    "fenerbahce sk": "Fenerbahce",
}


def map_opponent(raw_opponent: str) -> str:
    """
    Map a raw opponent string from Transfermarkt to our canonical club name.
    Returns the canonical name if found, otherwise "Unspecified".
    Empty string means no opponent data was present on TM.
    """
    if not raw_opponent or raw_opponent.strip() == "":
        return ""

    cleaned = raw_opponent.strip().lower()

    # Direct match in our club list
    if cleaned in CLUB_NAMES_LOWER:
        return CLUB_NAMES_LOWER[cleaned]

    # Alias match
    if cleaned in CLUB_ALIASES:
        return CLUB_ALIASES[cleaned]

    # Partial match — if any of our club names is a substring
    for name_lower, canonical in CLUB_NAMES_LOWER.items():
        if name_lower in cleaned or cleaned in name_lower:
            return canonical

    return "Unspecified"


# ---------------------------------------------------------------------------
# Browser factory (same settings as tm_squad_scraper.py)
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


def dismiss_cookies(driver: webdriver.Chrome) -> None:
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
        pass


# ---------------------------------------------------------------------------
# Core scraping: injury page for one player
# ---------------------------------------------------------------------------
def scrape_player_injuries(
    driver: webdriver.Chrome,
    player_name: str,
    player_tm_id: str,
    current_club: str,
    profile_url: str,
) -> list[InjuryRow]:
    """
    Navigate to a player's Transfermarkt injury history page and scrape all rows.
    URL pattern: https://www.transfermarkt.co.in/{slug}/verletzungen/spieler/{id}
    """
    # Build injury URL — MUST include /plus/1 to get full history
    # Correct format: https://www.transfermarkt.co.in/{slug}/verletzungen/spieler/{id}/plus/1
    slug_match = re.search(r"/([^/]+)/(?:profil|startseite)/spieler/", profile_url)
    if slug_match:
        slug = slug_match.group(1)
    else:
        slug = player_name.lower().replace(" ", "-")
    injury_url = f"https://www.transfermarkt.co.in/{slug}/verletzungen/spieler/{player_tm_id}/plus/1"

    log.info(f"  Injuries → {player_name} ({player_tm_id})")

    try:
        driver.get(injury_url)
    except Exception as e:
        log.warning(f"  Could not load injury page for {player_name}: {e}")
        return []

    dismiss_cookies(driver)
    time.sleep(random.uniform(2.0, 3.5))

    # ── Click the "Detailed" tab to get opponent column ──
    try:
        detailed_btn = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//a[normalize-space()='Detailed'] | //span[normalize-space()='Detailed']",
                )
            )
        )
        detailed_btn.click()
        time.sleep(1.5)
        log.info(f"  Clicked Detailed tab for {player_name}")
    except TimeoutException:
        log.info(f"  No Detailed tab found — using default view for {player_name}")

    # ── Wait for injury table ──
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//h2[contains(text(),'Injury') or contains(text(),'injury')] | //div[contains(@class,'verletzungen')]",
                )
            )
        )
    except TimeoutException:
        pass

    time.sleep(1.0)

    # ── Find all tables on the page ──
    all_tables = driver.find_elements(By.TAG_NAME, "table")
    injury_table = None

    for t in all_tables:
        # Look for a table that has injury-related headers
        headers = t.find_elements(By.TAG_NAME, "th")
        header_text = " ".join(h.text.strip().lower() for h in headers)
        if any(kw in header_text for kw in ["injury", "season", "from", "days"]):
            injury_table = t
            log.info(f"  Found injury table with headers: {header_text[:80]}")
            break

    # Fallback — first table.items on the page
    if not injury_table:
        items = driver.find_elements(By.CSS_SELECTOR, "table.items")
        if items:
            injury_table = items[0]
            log.info("  Using first table.items as fallback")

    if not injury_table:
        log.info(
            f"  No injury table found for {player_name} — clean record or blocked."
        )
        return []

    rows: list[InjuryRow] = []
    table_rows = injury_table.find_elements(By.CSS_SELECTOR, "tbody tr")

    for tr in table_rows:
        cells = tr.find_elements(By.TAG_NAME, "td")
        if len(cells) < 4:
            continue

        try:
            season = cells[0].text.strip() if len(cells) > 0 else ""
            injury_type = cells[1].text.strip() if len(cells) > 1 else ""
            injury_date = cells[2].text.strip() if len(cells) > 2 else ""
            return_date = cells[3].text.strip() if len(cells) > 3 else ""

            games_missed = ""
            raw_opponent = ""

            # Detailed view: cols are Season, Injury, from, until, Days, [Club logo], Games missed
            # Try to find opponent club via img title or link text in any cell
            for cell in cells:
                try:
                    img = cell.find_element(By.TAG_NAME, "img")
                    title = img.get_attribute("title") or img.get_attribute("alt") or ""
                    if title and title not in ("", player_name):
                        raw_opponent = title
                        break
                except NoSuchElementException:
                    pass
                try:
                    link = cell.find_element(By.TAG_NAME, "a")
                    href = link.get_attribute("href") or ""
                    if "/verein/" in href or "/startseite/" in href:
                        raw_opponent = link.text.strip() or raw_opponent
                        break
                except NoSuchElementException:
                    pass

            # Games missed is usually the last cell
            if len(cells) >= 6:
                games_missed = cells[-1].text.strip()

            opponent_mapped = map_opponent(raw_opponent)

            if not injury_type and not injury_date:
                continue

            rows.append(
                InjuryRow(
                    player_name=player_name,
                    player_tm_id=player_tm_id,
                    current_club=current_club,
                    season=season,
                    injury_type=injury_type,
                    injury_date=injury_date,
                    return_date=return_date,
                    games_missed=games_missed,
                    opponent_club=raw_opponent,
                    opponent_mapped=opponent_mapped,
                )
            )

        except Exception as e:
            log.debug(f"  Row parse error for {player_name}: {e}")
            continue

    log.info(f"  ✓ {len(rows)} injury records for {player_name}.")
    return rows


# ---------------------------------------------------------------------------
# Save helper
# ---------------------------------------------------------------------------
def save_csv(rows: list[InjuryRow], path: str, checkpoint: bool = False) -> None:
    if not rows:
        return
    save_path = path if not checkpoint else path.replace(".csv", "_checkpoint.csv")
    df = pd.DataFrame([vars(r) for r in rows])
    df.to_csv(save_path, index=False, encoding="utf-8-sig")
    log.info(f"  💾 Saved {len(rows)} rows → {save_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run(input_path: str, output_path: str, headless: bool = True) -> None:
    # Load squad data
    squad_df = pd.read_csv(input_path)
    required_cols = {"player_name", "player_tm_id", "club_name", "profile_url"}
    missing = required_cols - set(squad_df.columns)
    if missing:
        raise ValueError(f"squad_data.csv is missing columns: {missing}")

    # Drop players with no TM ID or profile URL
    squad_df = squad_df.dropna(subset=["player_tm_id", "profile_url"])
    squad_df["player_tm_id"] = squad_df["player_tm_id"].astype(str).str.strip()
    squad_df = squad_df[squad_df["player_tm_id"] != ""]

    total = len(squad_df)
    log.info(f"Loaded {total} players from {input_path}. Starting injury scrape...")

    driver = build_driver(headless=headless)
    all_injuries: list[InjuryRow] = []

    try:
        for i, row in enumerate(squad_df.itertuples(), 1):
            log.info(f"[{i}/{total}] {row.player_name} — {row.club_name}")

            injuries = scrape_player_injuries(
                driver=driver,
                player_name=str(row.player_name),
                player_tm_id=str(row.player_tm_id),
                current_club=str(row.club_name),
                profile_url=str(row.profile_url),
            )
            all_injuries.extend(injuries)

            # Checkpoint every 50 players
            if i % 50 == 0:
                save_csv(all_injuries, output_path, checkpoint=True)
                log.info(f"  Checkpoint: {len(all_injuries)} injury records so far.")

            # Polite delay between players: 3–6 seconds
            if i < total:
                time.sleep(random.uniform(3, 6))

    finally:
        driver.quit()
        log.info("Browser closed.")

    save_csv(all_injuries, output_path, checkpoint=False)

    # Summary
    log.info(
        f"\n✅ Done. {len(all_injuries)} total injury records saved to {output_path}"
    )
    if all_injuries:
        df = pd.DataFrame([vars(r) for r in all_injuries])
        log.info("\nOpponent mapping summary:")
        log.info(
            f"  Mapped to known club : {len(df[(df['opponent_mapped'] != 'Unspecified') & (df['opponent_mapped'] != '')])}"
        )
        log.info(
            f"  Unspecified (unknown): {(df['opponent_mapped'] == 'Unspecified').sum()}"
        )
        log.info(f"  No opponent data     : {(df['opponent_mapped'] == '').sum()}")
        log.info(
            f"\nTop injury types:\n{df['injury_type'].value_counts().head(10).to_string()}"
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape Transfermarkt injury history for all players in squad_data.csv"
    )
    parser.add_argument(
        "--input",
        "-i",
        default="data/raw/squad_data.csv",
        help="Path to squad_data.csv from tm_squad_scraper.py",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="data/raw/injury_data.csv",
        help="Output CSV path (default: data/raw/injury_data.csv)",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run Chrome visibly (useful for debugging)",
    )
    args = parser.parse_args()

    run(
        input_path=args.input,
        output_path=args.output,
        headless=not args.no_headless,
    )
