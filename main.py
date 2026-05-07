"""
main.py
-------
Reads gold/silver prices from data.json (written by bot.py),
injects them into template.html, and saves a screenshot as
poster_1.png, poster_2.png, etc.
"""

import os
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# ─────────────────────────────────────────────
#  1. CONFIG
# ─────────────────────────────────────────────

HTML_FILE = "template.html"

# ─────────────────────────────────────────────
#  2. LOAD PRICES FROM data.json
# ─────────────────────────────────────────────

script_dir = os.path.dirname(os.path.abspath(__file__))
data_json  = os.path.join(script_dir, "data.json")

if os.path.exists(data_json):
    with open(data_json, "r", encoding="utf-8") as f:
        prices = json.load(f)
    print(f"✅ Loaded prices: {prices}")
else:
    prices = {"gold_24": "7,450", "gold_22": "6,830", "silver": "92"}
    print("⚠️  data.json not found — using default values.")

PLACEHOLDERS = {
    "{{shop_name}}": "Sharma Jewellers",
    "{{gold_24}}":   prices.get("gold_24", "—"),
    "{{gold_22}}":   prices.get("gold_22", "—"),
    "{{silver}}":    prices.get("silver",  "—"),
}

# ─────────────────────────────────────────────
#  3. HELPER — auto-increment filename
# ─────────────────────────────────────────────

def get_next_filename(folder, base="poster", ext=".png"):
    i = 1
    while True:
        name = f"{base}_{i}{ext}"
        if not os.path.exists(os.path.join(folder, name)):
            return name
        i += 1

# ─────────────────────────────────────────────
#  4. BUILD PATHS
# ─────────────────────────────────────────────

html_path      = os.path.join(script_dir, HTML_FILE)
temp_html_path = os.path.join(script_dir, "_temp_poster.html")
output_file    = get_next_filename(script_dir)
output_path    = os.path.join(script_dir, output_file)

if not os.path.exists(html_path):
    raise FileNotFoundError(
        f"\n[ERROR] '{HTML_FILE}' not found.\n"
        f"Expected location: {html_path}\n"
        "Make sure template.html is in the same folder as this script."
    )

# ─────────────────────────────────────────────
#  5. INJECT VALUES INTO HTML
# ─────────────────────────────────────────────

with open(html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

for placeholder, value in PLACEHOLDERS.items():
    html_content = html_content.replace(placeholder, value)

with open(temp_html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

# ─────────────────────────────────────────────
#  6. SET UP HEADLESS CHROME
# ─────────────────────────────────────────────

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--window-size=1240,1754")

service = Service(ChromeDriverManager().install())
driver  = webdriver.Chrome(service=service, options=chrome_options)

# ─────────────────────────────────────────────
#  7. SCREENSHOT
# ─────────────────────────────────────────────

try:
    file_url = "file:///" + temp_html_path.replace(os.sep, "/")
    driver.get(file_url)

    poster_div = driver.find_element(By.ID, "poster")
    png_data   = poster_div.screenshot_as_png

    with open(output_path, "wb") as f:
        f.write(png_data)

    print(f"\n✅ Poster saved → {output_path}")

except Exception as e:
    print(f"\n❌ Error: {e}")

finally:
    driver.quit()
    if os.path.exists(temp_html_path):
        os.remove(temp_html_path)