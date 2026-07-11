from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

options = Options()
options.add_argument("--start-maximized")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
driver.get(
    "https://www.transfermarkt.com/yannick-eduardo/leistungsdatendetails/spieler/930998"
)
time.sleep(5)
for y in [400, 800, 1200, 1600]:
    driver.execute_script(f"window.scrollTo(0, {y});")
    time.sleep(0.5)
time.sleep(2)

rows = driver.find_elements(By.CSS_SELECTOR, "div[role='row']")
print(f"Rows found: {len(rows)}")
for r in rows[:5]:
    print("---")
    print(repr(r.text))

input("Press Enter to close...")
driver.quit()
