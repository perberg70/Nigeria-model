"""Run with Python and Playwright installed; CHROMIUM_PATH selects the browser."""

import csv
import os
import tempfile
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

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
                if number == 2:
                    assert page.locator(".policy-benchmark, .policy-gap").count() == 0
                    assert page.locator(".driver h2").count() == 4
                    assert page.locator(".driver > details.more").count() == 4
                    mix = page.locator(".driver > .mixpanel")
                    assert mix.is_visible()
                    assert "Set your energy mix" in mix.inner_text()
                    mix.locator("summary").first.click()
                    assert mix.locator("[data-src]").count() == 7
                    assert mix.locator(".mixbar").is_visible()
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    mix.locator("summary").first.click()
                if number == 4:
                    assert page.locator(".body > .tiles").count() == 1
                    assert page.locator(".fold-list").count() == 2
                    assert page.locator('[data-keep="em-explain"]').count() == 1
                    assert page.locator('[data-keep="el-explain"]').count() == 1
                    assert page.locator(".fold-list details[open]").count() == 0
                if number == 3:
                    sketches = page.locator(".card svg.sketch")
                    assert sketches.count() == 5
                    assert all(sketch.is_visible() for sketch in sketches.all())
                    curves = sketches.locator("path:last-child").evaluate_all(
                        "paths => paths.map(path => path.getAttribute('d'))"
                    )
                    assert len(set(curves)) == 5
                    assert "they are not data" in page.locator(".sketch-note").inner_text()
                if number > 1:
                    back = page.locator(".actions .back")
                    assert back.get_attribute("data-go") == str(number - 1)
                    page.mouse.move(0, 0)
                    assert (
                        back.evaluate("el => getComputedStyle(el).backgroundColor")
                        == "rgb(14, 92, 63)"
                    )
                    assert back.evaluate("el => getComputedStyle(el).color") == "rgb(255, 255, 255)"
                    back.click()
                    assert page.locator('#stepNav [aria-current="step"]').get_attribute(
                        "data-go"
                    ) == str(number - 1)
                    step(number)
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.set_viewport_size({"width": 1440, "height": 1000})
        step(2)
        page.locator(".mixpanel > summary").click()
        pin = page.locator('#content [data-pin="low|Solar"]')
        pin.check()
        assert page.locator("#ovl").is_hidden()
        source = page.locator('#content [data-src="low|Solar"]')
        source.focus()
        source.press("ArrowRight")
        assert page.locator("#ovl").is_hidden()
        assert page.locator(".mixpanel").get_attribute("open") is not None
        page.evaluate("state.sourceMix = {}; render()")
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
            assert page.locator(".mapbox g.climate-region").count() == 10
            assert page.locator(".mapbox .climate-region path").count() == 64
            assert page.locator("#regionDetail details[open]").count() == 0
            for area in page.locator(".mapbox g.climate-region").all():
                area.focus()
                expect(page.locator("#tt")).to_have_css("opacity", "1")
                assert "median" in page.locator("#tt").inner_text()
                area.dispatch_event("mousemove", {"clientX": 100, "clientY": 100})
                assert page.locator("#tt").inner_text() == area.get_attribute("data-tooltip")
            region = page.locator('[data-region="Andean"]').first
            region.focus()
            region.press("Enter")
            assert "Bogotá" in page.locator("#regionDetail").inner_text()
            assert page.locator("#regionDetail details[open]").count() == 1
            page.locator("#regionDetail details[open] > summary").click()
            assert not page.locator("#regionDetail table").first.is_visible()
            assert "NaN" not in page.locator("#content").inner_text()
        step(1)
        page.locator("#finder").select_option("BRA")
        step(2)
        assert page.locator(".policy-benchmark, .policy-gap").count() == 0
        step(6)
        assert "Brazil" in page.locator("h1").inner_text()
        step(1)
        page.locator("#finder").select_option("COL")
        step(2)
        for driver in ("elec", "mix"):
            box = page.locator(f'.driver:has([data-drv="{driver}"])')
            box.locator("summary").first.click()
            assert "About this lever" in box.inner_text()
        # Disclosure stays open when a native slider change rebuilds the screen.
        page.locator('[data-drv="elec"]').focus()
        page.locator('[data-drv="elec"]').press("ArrowRight")
        assert page.locator('[data-keep="driver-elec"]').get_attribute("open") is not None
        # Export captures current settings and the results from every results screen.
        step(6)
        expected = {}
        for number in (4, 5, 6):
            step(number)
            expected[number] = page.locator(".tile .val").all_text_contents()
        settings_before = page.evaluate("JSON.stringify(state)")
        with tempfile.TemporaryDirectory() as tmp:
            with page.expect_download() as download:
                page.locator('[data-save="csv"]').click()
            path = Path(tmp) / "outcome.csv"
            download.value.save_as(path)
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.reader(handle))
            assert rows[0] == ["Section", "Item", "Value", "Detail"]
            assert all(len(row) == 4 for row in rows)
            assert any(row[1:3] == ["Global scenario", "SSP5-8.5"] for row in rows)
            assert any(row[1:3] == ["National climate mitigation target", "-59%"] for row in rows)
            for values in expected.values():
                assert all(any(row[2] == value for row in rows) for value in values)
            assert any(row[0] == "Fixed assumptions" for row in rows)
            assert any("ODbL" in row[2] for row in rows)
            with page.expect_popup() as opened:
                page.locator('[data-save="pdf"]').click()
            report = opened.value
            report.on("pageerror", lambda error: errors.append(str(error)))
            report.wait_for_selector("#report h1")
            assert report.locator("#report svg").count() >= 4
            assert report.locator('#report a[href$="MAP-LICENSE.txt"]').count() == 1
            for values in expected.values():
                assert all(value in report.locator("#report").inner_text() for value in values)
            report.pdf(path=str(Path(tmp) / "outcome.pdf"), print_background=True)
            assert (Path(tmp) / "outcome.pdf").stat().st_size > 10000
            report.close()
        assert page.evaluate("JSON.stringify(state)") == settings_before
        # A blocked popup still prints the complete report, then restores the UI.
        page.evaluate("""() => {
            window.open = () => null;
            window.print = () => { window.printCalled = true; };
        }""")
        page.locator('[data-save="pdf"]').click()
        assert page.evaluate("window.printCalled") is True
        assert "Fixed assumptions" in page.locator("#report").inner_text()
        page.evaluate("window.dispatchEvent(new Event('afterprint'))")
        assert page.locator("#report").inner_text() == ""
        assert page.evaluate("JSON.stringify(state)") == settings_before
        page.locator(".actions .wide").click()
        assert page.locator('#stepNav [aria-current="step"]').get_attribute("data-go") == "2"
        assert not errors, errors
        browser.close()
        print(
            "PASS: six screens, mobile layout, live slider, baseline isolation, "
            "five SSPs, keyboard map drilldown, country switching, back navigation, PDF/CSV exports"
        )


if __name__ == "__main__":
    main()
