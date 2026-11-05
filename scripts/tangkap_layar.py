"""
scripts/tangkap_layar.py - Mengambil screenshot setiap tab untuk README (butuh Playwright + Chromium).

    streamlit run app.py --server.port 8601 --server.headless true &
    python scripts/tangkap_layar.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://localhost:8601"
KELUARAN = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
# (nama tab, nama berkas, piksel yang di-scroll sebelum memotret)
TAB = [
    ("World map", "01_peta.png", 300),
    ("Who's who", "02_siapa.png", 330),
    ("Timeline", "03_timeline.png", 330),
    ("Controversies", "04_kontroversi.png", 330),
    ("Follow the revenue", "05_pendapatan.png", 330),
    ("Data & sources", "06_data.png", 330),
    ("How it works", "07_cara_kerja.png", 330),
]


def scroll(page, y: int) -> None:
    page.evaluate(f"document.querySelector('section.main, [data-testid=\"stMain\"]').scrollTo(0, {y})")


def main() -> None:
    KELUARAN.mkdir(parents=True, exist_ok=True)
    exe = sys.argv[1] if len(sys.argv) > 1 else None
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page.goto(URL, wait_until="networkidle", timeout=120_000)
        page.wait_for_selector("[role='tab']", timeout=180_000)
        page.wait_for_timeout(5000)
        for nama, berkas, y in TAB:
            page.get_by_role("tab", name=nama).click()
            page.wait_for_timeout(3500)
            scroll(page, y)
            page.wait_for_timeout(1200)
            page.screenshot(path=str(KELUARAN / berkas))
            print("ok", berkas)
        page.get_by_role("tab", name="Timeline").click()
        page.get_by_text("Learning mode").click()
        page.wait_for_timeout(2500)
        page.locator("summary:visible").first.click()
        page.wait_for_timeout(1500)
        page.locator("summary:visible").first.scroll_into_view_if_needed()
        page.wait_for_timeout(800)
        page.screenshot(path=str(KELUARAN / "08_mode_belajar.png"))
        print("ok 08_mode_belajar.png")
        if page.locator("[data-testid='stException']").count():
            print("PERINGATAN: ada exception di halaman")
        browser.close()


if __name__ == "__main__":
    main()
