from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    out = Path("tmp/ui-check")
    out.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, size in [
            ("desktop", {"width": 1440, "height": 920}),
            ("mobile", {"width": 390, "height": 844}),
        ]:
            page = browser.new_page(viewport=size)
            page.goto("http://127.0.0.1:8001/", wait_until="networkidle")
            page.evaluate(
                """
                () => {
                    const bubble = window.document.querySelector('.message.agent .bubble');
                    bubble.textContent = 'The ISS is near Kazakhstan!\\n\\n[OpenStreetMap](https://www.openstreetmap.org/?mlat=43.23&mlon=51.83#map=4/43.23/51.83)';
                    window.renderRichAgentBubbleForTest(bubble);
                }
                """
            )
            page.locator(".map-card iframe").wait_for(state="visible", timeout=5000)
            page.wait_for_timeout(2500)
            mascot_box = page.locator(".mascot").bounding_box()
            chat_box = page.locator(".chat-panel").bounding_box()
            map_box = page.locator(".map-card iframe").bounding_box()
            overflow_x = page.evaluate(
                "document.documentElement.scrollWidth > document.documentElement.clientWidth"
            )
            page.screenshot(path=str(out / f"{name}.png"), full_page=True)
            print(
                f"{name}: title={page.title()!r} mascot={bool(mascot_box)} "
                f"chat={bool(chat_box)} map={bool(map_box)} overflow_x={overflow_x}"
            )
        browser.close()


if __name__ == "__main__":
    main()
