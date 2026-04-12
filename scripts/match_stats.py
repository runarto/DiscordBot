from playwright.sync_api import sync_playwright
import time


def capture_match_details(match_id: int) -> dict:
    page_url = f"https://www.fotmob.com/match/{match_id}"
    captured = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context().new_page()

        def handle_response(response):
            if "matchDetails?matchId=" in response.url:
                try:
                    captured["url"] = response.url
                    captured["status"] = response.status
                    captured["body"] = response.text()
                except Exception as e:
                    captured["error"] = str(e)

        page.on("response", handle_response)
        page.goto(page_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        browser.close()

    return captured


if __name__ == "__main__":
    match_ids = [4385397, 4385393]
    for match_id in match_ids:
        time.sleep(1)  # Be polite and avoid hitting the server too hard
        result = capture_match_details(match_id)
        print(f"Match ID: {match_id}")
        print(f"Captured URL: {result.get('url')}")
        print(f"Status: {result.get('status')}")
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Body length: {len(result.get('body', ''))} characters")
        print("-" * 40)
