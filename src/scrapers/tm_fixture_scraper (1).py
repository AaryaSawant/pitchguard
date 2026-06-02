"""
PitchGuard — Transfermarkt Fixture Scraper (Arnav)
===================================================
Scrapes fixture lists for all 100 clubs across 6 seasons.
Uses undetected_chromedriver with a visible Chrome window.

Usage:
    python tm_fixture_scraper.py --output data/raw/club_fixtures.csv

Requirements:
    pip install undetected-chromedriver selenium pandas
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
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("tm_fixtures")

CLUBS = [
    ("Arsenal",                  "fc-arsenal",               "11"),
    ("Aston Villa",              "aston-villa",              "405"),
    ("Brentford",                "brentford-fc",             "1148"),
    ("Brighton & Hove Albion",   "brighton-hove-albion",     "1237"),
    ("Chelsea",                  "fc-chelsea",               "631"),
    ("Crystal Palace",           "crystal-palace",           "873"),
    ("Everton",                  "fc-everton",               "29"),
    ("Fulham",                   "fc-fulham",                "931"),
    ("Ipswich Town",             "ipswich-town",             "677"),
    ("Leicester City",           "leicester-city",           "1003"),
    ("Liverpool",                "fc-liverpool",             "31"),
    ("Manchester City",          "manchester-city",          "281"),
    ("Manchester United",        "manchester-united",        "985"),
    ("Newcastle United",         "newcastle-united",         "762"),
    ("Nottingham Forest",        "nottingham-forest",        "703"),
    ("Southampton",              "fc-southampton",           "180"),
    ("Tottenham Hotspur",        "tottenham-hotspur",        "148"),
    ("West Ham United",          "west-ham-united",          "379"),
    ("Wolverhampton Wanderers",  "wolverhampton-wanderers",  "543"),
    ("Bournemouth",              "afc-bournemouth",          "989"),
    ("Real Madrid",              "real-madrid",              "418"),
    ("FC Barcelona",             "fc-barcelona",             "131"),
    ("Atletico Madrid",          "atletico-de-madrid",       "13"),
    ("Sevilla FC",               "fc-sevilla",               "368"),
    ("Real Betis",               "real-betis-balompie",      "150"),
    ("Real Sociedad",            "real-sociedad",            "681"),
    ("Athletic Bilbao",          "athletic-club",            "621"),
    ("Villarreal CF",            "villarreal-cf",            "383"),
    ("Valencia CF",              "fc-valencia",              "1049"),
    ("Celta Vigo",               "rc-celta-de-vigo",         "940"),
    ("Rayo Vallecano",           "rayo-vallecano",           "367"),
    ("Osasuna",                  "ca-osasuna",               "331"),
    ("Getafe CF",                "getafe-cf",                "3709"),
    ("Girona FC",                "girona-fc",                "12321"),
    ("UD Las Palmas",            "ud-las-palmas",            "472"),
    ("Deportivo Alaves",         "deportivo-alaves",         "1108"),
    ("RCD Mallorca",             "rcd-mallorca",             "237"),
    ("CD Leganes",               "cd-leganes",               "5905"),
    ("Real Valladolid",          "real-valladolid-cf",       "366"),
    ("Espanyol",                 "rcd-espanyol-barcelona",   "714"),
    ("Bayern Munich",            "fc-bayern-munchen",        "27"),
    ("Borussia Dortmund",        "borussia-dortmund",        "16"),
    ("Bayer Leverkusen",         "bayer-04-leverkusen",      "15"),
    ("RB Leipzig",               "rasenballsport-leipzig",   "23826"),
    ("Eintracht Frankfurt",      "eintracht-frankfurt",      "24"),
    ("VfB Stuttgart",            "vfb-stuttgart",            "79"),
    ("Werder Bremen",            "sv-werder-bremen",         "86"),
    ("SC Freiburg",              "sport-club-freiburg",      "60"),
    ("TSG Hoffenheim",           "tsg-1899-hoffenheim",      "533"),
    ("Borussia Monchengladbach", "borussia-monchengladbach", "23"),
    ("FC Augsburg",              "fc-augsburg",              "167"),
    ("1. FC Union Berlin",       "1-fc-union-berlin",        "89"),
    ("VfL Bochum",               "vfl-bochum",               "80"),
    ("SV Darmstadt 98",          "sv-darmstadt-98",          "105"),
    ("1. FC Heidenheim",         "1-fc-heidenheim-1846",     "2036"),
    ("Holstein Kiel",            "holstein-kiel",            "4372"),
    ("FC St. Pauli",             "fc-st-pauli",              "35"),
    ("VfL Wolfsburg",            "vfl-wolfsburg",            "82"),
    ("Inter Milan",              "inter-mailand",            "46"),
    ("AC Milan",                 "ac-mailand",               "5"),
    ("Juventus",                 "juventus-turin",           "506"),
    ("AS Roma",                  "as-rom",                   "12"),
    ("SSC Napoli",               "ssc-neapel",               "6195"),
    ("Lazio",                    "lazio-rom",                "398"),
    ("Atalanta",                 "atalanta-bergamo",         "800"),
    ("Fiorentina",               "acf-fiorentina",           "430"),
    ("Torino",                   "fc-turin",                 "416"),
    ("Bologna",                  "fc-bologna",               "1025"),
    ("Genoa",                    "genua-cfc",                "252"),
    ("Cagliari",                 "cagliari-calcio",          "1390"),
    ("Hellas Verona",            "hellas-verona",            "276"),
    ("Monza",                    "ac-monza",                 "9462"),
    ("Udinese",                  "udinese-calcio",           "410"),
    ("Como",                     "como-1907",                "2324"),
    ("Venezia",                  "fc-venedig",               "685"),
    ("Parma",                    "parma-calcio-1913",        "130"),
    ("Empoli",                   "fc-empoli",                "749"),
    ("Lecce",                    "us-lecce",                 "4884"),
    ("Paris Saint-Germain",      "paris-saint-germain",      "583"),
    ("Olympique de Marseille",   "olympique-marseille",      "244"),
    ("Olympique Lyonnais",       "olympique-lyon",           "1041"),
    ("AS Monaco",                "as-monaco",                "162"),
    ("Lille OSC",                "losc-lille",               "1082"),
    ("OGC Nice",                 "ogc-nizza",                "417"),
    ("Stade Rennais",            "stade-rennais",            "273"),
    ("RC Lens",                  "rc-lens",                  "826"),
    ("Montpellier HSC",          "montpellier-hsc",          "969"),
    ("Strasbourg",               "rc-strasbourg-alsace",     "667"),
    ("FC Nantes",                "fc-nantes",                "995"),
    ("Toulouse FC",              "toulouse-fc",              "415"),
    ("Stade Brestois",           "stade-brestois-29",        "3911"),
    ("Angers SCO",               "angers-sco",               "1023"),
    ("Le Havre AC",              "le-havre-ac",              "738"),
    ("Auxerre",                  "aj-auxerre",               "69"),
    ("Saint-Etienne",            "as-saint-etienne",         "618"),
    ("Girondins Bordeaux",       "fc-girondins-bordeaux",    "374"),
    ("Galatasaray",              "galatasaray-sk",           "141"),
    ("Fenerbahce",               "fenerbahce-sk",            "36"),
    ("Besiktas",                 "besiktas-jk",              "114"),
    ("Trabzonspor",              "trabzonspor",              "449"),
]

SEASON_YEARS     = [2019, 2020, 2021, 2022, 2023, 2024]
BASE_URL         = (
    "https://www.transfermarkt.co.in/{slug}/spielplandatum/verein/{tm_id}"
    "/saison_id/{year}/wettbewerb_id//datum_von/0000-00-00"
    "/datum_bis/0000-00-00/day/0/plus/1"
)
CHECKPOINT_EVERY = 10
DELAY_MIN        = 4.0
DELAY_MAX        = 7.0


def build_driver() -> uc.Chrome:
    opts = uc.ChromeOptions()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--lang=en-GB")
    # Use locally cached ChromeDriver — avoids network download
    driver_path = ChromeDriverManager().install()
    driver = uc.Chrome(options=opts, driver_executable_path=driver_path)
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


def parse_fixtures(driver: uc.Chrome, club_name: str,
                   tm_id: str, season_year: int) -> list[dict]:
    season_label = f"{season_year}/{str(season_year + 1)[-2:]}"

    # Wait for page body
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
    except TimeoutException:
        log.warning(f"    Page timeout for {club_name} {season_label}")
        return []

    time.sleep(random.uniform(2.5, 4.0))

    # Find fixture table rows — TM club fixture pages use real <table> elements
    table_rows = []
    for selector in [
        "div#yw1 table tbody tr",
        "table.items tbody tr",
        "div.responsive-table table tbody tr",
    ]:
        try:
            table_rows = driver.find_elements(By.CSS_SELECTOR, selector)
            if table_rows:
                break
        except NoSuchElementException:
            continue

    if not table_rows:
        log.warning(f"    No fixture table for {club_name} {season_label}")
        return []

    rows = []
    for tr in table_rows:
        cells = tr.find_elements(By.CSS_SELECTOR, "td")
        if not cells or len(cells) < 3:
            continue

        cell_texts = [c.text.strip() for c in cells]

        row = {
            "club_name":   club_name,
            "club_tm_id":  tm_id,
            "season":      season_label,
            "match_date":  "",
            "competition": "",
            "home_away":   "",
            "opponent":    "",
            "result":      "",
        }

        # Date
        for txt in cell_texts:
            if re.search(r"\d{2}/\d{2}/\d{2,4}", txt):
                row["match_date"] = txt
                break

        if not row["match_date"]:
            continue

        # Competition from image title
        try:
            img = tr.find_element(By.CSS_SELECTOR, "img[title]")
            row["competition"] = img.get_attribute("title") or ""
        except NoSuchElementException:
            pass

        # Home/Away
        for txt in cell_texts:
            if txt in ("H", "A", "N"):
                row["home_away"] = txt
                break

        # Opponent — last meaningful link text
        try:
            links = tr.find_elements(By.CSS_SELECTOR, "a")
            for a in reversed(links):
                txt = a.text.strip()
                if txt and len(txt) > 2 and not re.match(r"^\d", txt):
                    row["opponent"] = txt
                    break
        except NoSuchElementException:
            pass

        # Result
        for txt in cell_texts:
            if re.match(r"\d+:\d+|\d+-\d+", txt):
                row["result"] = txt
                break

        rows.append(row)

    log.info(f"    ✓ {len(rows)} fixtures for {club_name} {season_label}")
    return rows


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


def run(output_path: str) -> None:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Resume support
    already_done: set[tuple] = set()
    if out.exists():
        existing = pd.read_csv(out, dtype=str)
        for _, r in existing.iterrows():
            already_done.add((str(r["club_tm_id"]), str(r["season"])))
        log.info(f"Resuming — {len(already_done)} club-season combos already done.")

    driver = build_driver()
    cookies_dismissed = False
    buffer: list[dict] = []
    total = len(CLUBS)

    try:
        for i, (club_name, slug, tm_id) in enumerate(CLUBS, 1):
            log.info(f"[{i}/{total}] {club_name}")

            for year in SEASON_YEARS:
                season_label = f"{year}/{str(year + 1)[-2:]}"
                if (tm_id, season_label) in already_done:
                    log.info(f"  {season_label} already scraped — skipping.")
                    continue

                url = BASE_URL.format(slug=slug, tm_id=tm_id, year=year)
                log.info(f"  {season_label}")
                time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

                try:
                    driver.get(url)
                except Exception as e:
                    log.warning(f"  Load error: {e}")
                    continue

                if not cookies_dismissed:
                    dismiss_cookies(driver)
                    cookies_dismissed = True

                rows = parse_fixtures(driver, club_name, tm_id, year)
                buffer.extend(rows)

            if i % CHECKPOINT_EVERY == 0:
                append_csv(buffer, out)
                buffer = []
                log.info(f"💾 Checkpoint saved at club {i}/{total}")

    except KeyboardInterrupt:
        log.info("\n⚠️  Ctrl+C — saving progress...")
    finally:
        append_csv(buffer, out)
        try:
            driver.quit()
        except Exception:
            pass
        log.info("Browser closed.")

    if out.exists():
        final = pd.read_csv(out)
        log.info(f"\n✅ Done. {len(final)} fixture rows → {out}")
        log.info(f"   Clubs   : {final['club_name'].nunique()}")
        log.info(f"   Seasons : {sorted(final['season'].unique())}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--oufictput", "-o", default="data/raw/club_fixtures.csv")
    args = p.parse_args()
    run(output_path=args.output)
