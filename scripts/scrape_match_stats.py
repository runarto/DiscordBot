"""
Bulk-scrape FotMob matchDetails for every historical match and save raw JSON.

Output directory: match_stats/{match_id}.json

Usage:
    python -m scripts.scrape_match_stats [--limit N] [--delay 5.0]

Each file is the raw JSON body of:
    https://www.fotmob.com/api/data/matchDetails?matchId={match_id}

Already-scraped matches are skipped on re-run.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from playwright.async_api import async_playwright

from db.db_interface import DB

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "match_stats")
DB_PATH = "infobase.db"
API_PATTERN = "matchDetails?matchId="
BRAVE_PATH = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"

log = logging.getLogger(__name__)


def already_scraped(match_id: int) -> bool:
    return os.path.exists(os.path.join(OUT_DIR, f"{match_id}.json"))


async def scrape_all(match_ids: list[int], delay: float) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    total = len(match_ids)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=BRAVE_PATH,
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context()
        page = await context.new_page()

        for idx, match_id in enumerate(match_ids, 1):
            if already_scraped(match_id):
                log.info("[%d/%d] %s — already scraped, skipping", idx, total, match_id)
                continue

            try:
                async with page.expect_response(
                    lambda r: API_PATTERN in r.url,
                    timeout=20_000,
                ) as resp_info:
                    await page.goto(
                        f"https://www.fotmob.com/match/{match_id}",
                        wait_until="domcontentloaded",
                        timeout=60_000,
                    )

                resp = await resp_info.value
                if resp.status != 200:
                    log.warning("[%d/%d] %s — HTTP %s, skipping", idx, total, match_id, resp.status)
                    await asyncio.sleep(delay)
                    continue
                body = await resp.text()
                data = json.loads(body)

                out_path = os.path.join(OUT_DIR, f"{match_id}.json")
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False)

                log.info("[%d/%d] %s — saved", idx, total, match_id)

            except Exception as e:
                log.warning("[%d/%d] %s — %s", idx, total, match_id, e)

            await asyncio.sleep(delay)

        await browser.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Max matches to scrape")
    parser.add_argument("--delay", type=float, default=5.0, help="Seconds between requests")
    args = parser.parse_args()

    db = DB(DB_PATH)
    rows = db.get_historical_matches()

    # Skip 2018 — FotMob has no matchDetails for those
    match_ids = sorted(set(
        row["match_id"] for row in rows
        if row["match_id"] is not None and not row["kick_off_time"].startswith("2018")
    ))

    pending = [mid for mid in match_ids if not already_scraped(mid)]
    log.info(
        "%d total match IDs, %d already scraped, %d to fetch",
        len(match_ids),
        len(match_ids) - len(pending),
        len(pending),
    )

    if args.limit:
        pending = pending[: args.limit]

    asyncio.run(scrape_all(pending, delay=args.delay))
    log.info("Done.")


if __name__ == "__main__":
    main()
