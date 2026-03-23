"""
pagerinfo/scheduler.py
Runs the scraper on a randomized schedule with jitter to avoid
pattern detection. Also sends push notifications when new posts arrive.
"""

import asyncio
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "fb_digest"))

from config import Config
from database import Database
from scraper import run_scraper
from notifier import send_push_notifications


BASE_INTERVAL_MINUTES = 30   # time invterval for checking our facebook wall
JITTER_MINUTES        = 8    # ± (this is called 'jitter') > random interval to add/substract from the base interval (to avoid 'bot' detection)
MIN_INTERVAL_MINUTES  = 15   # minimum time between checking our wall (it is most likely too conservative, aka i guess normal person checks their wall quite often)


def next_wait_seconds() -> int:
    jitter  = random.uniform(-JITTER_MINUTES, JITTER_MINUTES)
    minutes = max(MIN_INTERVAL_MINUTES, BASE_INTERVAL_MINUTES + jitter)
    return int(minutes * 60)


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


async def run_cycle(config: Config, db: Database):
    log("Starting scrape cycle...")
    try:
        new_count = await run_scraper(config, db)
        log(f"Cycle complete — {new_count} new posts")
        if new_count > 0:
            await send_push_notifications(new_count)
    except Exception as e:
        log(f"Scrape error: {e}")


async def main():
    log("PagerInfo scheduler started")
    config = Config.load(str(Path(__file__).parent.parent / "fb_digest/config.yaml"))
    db     = Database(Path(__file__).parent / "data/digest.db")

    while True:
        await run_cycle(config, db)
        wait = next_wait_seconds()
        next_run = datetime.fromtimestamp(time.time() + wait).strftime("%H:%M:%S")
        log(f"Next run at {next_run} ({wait//60}m {wait%60}s)")
        await asyncio.sleep(wait)


if __name__ == "__main__":
    asyncio.run(main())
