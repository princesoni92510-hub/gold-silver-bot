"""
poster_gen.py
-------------
- Scans /templates folder for .html files
- Injects gold/silver prices into each template
- Takes headless Chrome screenshot of #poster div
- Saves images to /output folder
- Returns list of (caption, image_path) for Telegram
"""

import os
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

BASE_DIR      = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUT_DIR    = BASE_DIR / "output"
TEMP_HTML     = BASE_DIR / "_temp.html"

# Create output folder if it doesn't exist
OUTPUT_DIR.mkdir(exist_ok=True)


def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1240,1754")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def screenshot_template(driver, html_path: Path, output_path: Path, prices: dict) -> bool:
    html = html_path.read_text(encoding="utf-8")
    html = html.replace("{{gold_24}}", prices.get("gold_24", "—"))
    html = html.replace("{{gold_22}}", prices.get("gold_22", "—"))
    html = html.replace("{{silver}}",  prices.get("silver",  "—"))
    TEMP_HTML.write_text(html, encoding="utf-8")

    try:
        file_url = "file:///" + str(TEMP_HTML).replace(os.sep, "/")
        driver.get(file_url)
        poster = driver.find_element(By.ID, "poster")
        poster.screenshot(str(output_path))
        return True
    except Exception as e:
        print(f"❌ Error screenshotting {html_path.name}: {e}")
        return False


def generate_all_posters(prices: dict) -> list:
    templates = sorted(TEMPLATES_DIR.glob("*.html"))

    if not templates:
        print("⚠️  No .html files found in /templates folder.")
        return []

    print(f"\n📂 Found {len(templates)} template(s): {[t.name for t in templates]}")

    results = []
    driver  = get_driver()

    try:
        for template_path in templates:
            stem        = template_path.stem
            output_path = OUTPUT_DIR / f"{stem}.png"
            caption     = stem.replace("_", " ").title()

            print(f"  🖨️  Generating: {caption}...")
            success = screenshot_template(driver, template_path, output_path, prices)

            if success:
                results.append((caption, output_path))
                print(f"  ✅ Saved: {output_path.name}")
            else:
                print(f"  ❌ Failed: {template_path.name}")
    finally:
        driver.quit()
        if TEMP_HTML.exists():
            TEMP_HTML.unlink()

    print(f"\n✅ Generated {len(results)}/{len(templates)} posters.\n")
    return results