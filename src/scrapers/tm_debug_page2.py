"""
Debug exactly what's inside div[role='table'] after scroll.
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

url = (
    "https://www.transfermarkt.com/yannick-eduardo/leistungsdatendetails/spieler/930998"
)
driver.get(url)
time.sleep(5)

# Scroll
for y in [400, 800, 1200, 1600]:
    driver.execute_script(f"window.scrollTo(0, {y});")
    time.sleep(0.8)
time.sleep(3)

print(f"Title: {driver.title}")

# Find the virtual table
tables = driver.find_elements(By.CSS_SELECTOR, "div[role='table']")
print(f"\ndiv[role='table'] count: {len(tables)}")

if tables:
    t = tables[0]
    # Try different row selectors
    for sel in ["div[role='row']", "div[role='rowgroup']", "> div", "div"]:
        els = t.find_elements(By.CSS_SELECTOR, sel)
        print(f"  '{sel}': {len(els)} elements")
        if els and len(els) < 20:
            for i, el in enumerate(els[:5]):
                print(
                    f"    [{i}] class='{el.get_attribute('class')}' text='{el.text[:80]}'"
                )

    # Print raw innerHTML snippet
    inner = driver.execute_script("return arguments[0].innerHTML;", t)
    print(f"\n  innerHTML (first 1000 chars):\n{inner[:1000]}")

input("\nPress Enter to close...")
driver.quit()
