"""Run with Python and Playwright installed; CHROMIUM_PATH selects the browser."""

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH", "/usr/bin/chromium"),
            headless=True,
            args=["--no-sandbox"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content((ROOT / "prototype/colombia/colombia-prototype.html").read_text())

        def step(number):
            page.locator(f'#stepNav [data-go="{number}"]').click()
            assert page.locator('#stepNav [aria-current="step"]').count() == 1

        for width in (1440, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            for number in range(1, 7):
                step(number)
                assert page.locator("h1").inner_text()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.set_viewport_size({"width": 1440, "height": 1000})
        step(4)
        before = page.locator(".tile .val").all_text_contents()
        baseline = page.evaluate("COUNTRY.baselineAt(2050)")
        step(2)
        slider = page.locator('[data-drv="mitigation"]')
        slider.focus()
        slider.press("ArrowRight")
        assert "-59%" in page.locator("#settingsStrip").inner_text()
        assert page.locator('[data-drv="mitigation"]').input_value() == "-59"
        step(4)
        assert before != page.locator(".tile .val").all_text_contents()
        assert page.evaluate("COUNTRY.baselineAt(2050)") == baseline
        for scenario in ("ssp119", "ssp126", "ssp245", "ssp370", "ssp585"):
            step(3)
            page.locator(f'[data-ssp="{scenario}"]').click()
            page.keyboard.press("Escape")
            step(6)
            assert page.locator(".mapbox .climate-region").count() == 66
            region = page.locator('[data-region="Andean"]').first
            region.focus()
            region.press("Enter")
            assert "Bogotá" in page.locator("#regionDetail").inner_text()
            assert "NaN" not in page.locator("#content").inner_text()
        step(1)
        page.locator("#finder").select_option("BRA")
        step(6)
        assert "Brazil" in page.locator("h1").inner_text()
        step(1)
        page.locator("#finder").select_option("COL")
        step(2)
        for driver in ("elec", "mix"):
            box = page.locator(f'.driver:has([data-drv="{driver}"])')
            box.locator("summary").first.click()
            assert "About this lever" in box.inner_text()
        assert not errors, errors
        browser.close()
        print(
            "PASS: six screens, mobile layout, live slider, baseline isolation, "
            "five SSPs, keyboard map drilldown, country switching"
        )


if __name__ == "__main__":
    main()
