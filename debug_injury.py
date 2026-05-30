"""
Debug script — loads David Raya's injury page and prints everything we see.
Run: python debug_injury.py
"""
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

def build_driver():
    opts = Options()
    # VISIBLE browser
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    opts.add_argument("--lang=en-GB")
    opts.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver

driver = build_driver()

# Exact URL from Transfermarkt that works
url = "https://www.transfermarkt.com/david-raya/verletzungen/spieler/262749/plus/1"
print(f"\nLoading: {url}")
driver.get(url)
time.sleep(6)

print(f"Page title : {driver.title}")
print(f"Current URL: {driver.current_url}")

# Try cookie dismiss
try:
    btn = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.XPATH,
            "//button[contains(., 'Agree') or contains(., 'Accept') or @id='onetrust-accept-btn-handler']"
        ))
    )
    btn.click()
    print("Cookie banner dismissed")
    time.sleep(2)
except TimeoutException:
    print("No cookie banner")

# ── What tables exist? ──
tables = driver.find_elements(By.TAG_NAME, "table")
print(f"\nAll <table> elements on page: {len(tables)}")
for i, t in enumerate(tables):
    cls = t.get_attribute("class") or ""
    trs = t.find_elements(By.TAG_NAME, "tr")
    print(f"  [{i}] class='{cls}'  rows={len(trs)}")

# ── Try every likely selector ──
selectors = [
    "table.items",
    "table.standard_tabelle",
    "#verletzungen table",
    "div.responsive-table table",
    "div#yw1 table",
    "table[class*='item']",
]
print("\nSelector probe:")
for sel in selectors:
    els = driver.find_elements(By.CSS_SELECTOR, sel)
    print(f"  {sel!r:45s} → {len(els)} element(s)")

# ── Print raw HTML of first 2000 chars of body ──
body_html = driver.find_element(By.TAG_NAME, "body").get_attribute("innerHTML")[:3000]
print(f"\nBody HTML preview (first 3000 chars):\n{body_html}")

print("\n--- Keeping browser open 40s so you can inspect the page ---")
time.sleep(40)
driver.quit()
