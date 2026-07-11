import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

options = uc.ChromeOptions()
options.add_argument("--start-maximized")
driver = uc.Chrome(options=options, version_main=149)

url = (
    "https://www.transfermarkt.com/yannick-eduardo/leistungsdatendetails/spieler/930998"
)
driver.get(url)
time.sleep(4)

# Scroll down to trigger lazy load
driver.execute_script("window.scrollTo(0, 600);")
time.sleep(2)
driver.execute_script("window.scrollTo(0, 1200);")
time.sleep(2)

print(f"Title: {driver.title}")

# Find all tables on page
tables = driver.find_elements(By.TAG_NAME, "table")
print(f"\nTotal tables found: {len(tables)}")
for i, t in enumerate(tables):
    cls = t.get_attribute("class")
    print(
        f"  table[{i}] class='{cls}' | rows={len(t.find_elements(By.TAG_NAME, 'tr'))}"
    )

input("\nPress Enter to close...")
driver.quit()
