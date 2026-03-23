"""
fb_digest/scraper.py
Scrapes Facebook posts using Playwright with a saved browser session.
"""

import asyncio
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, BrowserContext, Page

from config import Config
from database import Database


SESSION_FILE = Path("data/session.json")


async def human_delay(min_ms: int = 800, max_ms: int = 2400):
    #Random delay to mimic human scrolling behavior
    await asyncio.sleep(random.randint(min_ms, max_ms) / 1000)


#a function to scroll down (relatively slow)
async def slow_scroll(page: Page, steps: int = 8, pause_ms: int = 1200):
    for _ in range(steps):
        scroll_amount = random.randint(400, 900)
        await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        await asyncio.sleep(pause_ms / 1000 + random.uniform(0, 0.5))


#login must have been manual so we operate on saved session
async def save_session(context: BrowserContext):
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    await context.storage_state(path=str(SESSION_FILE))
    print("Session saved.")


async def login_flow(page: Page, context: BrowserContext):
    print("\nNo saved session found. Opening browser for manual login...")
    print("Please log in to Facebook in the browser window.")
    print("The script will continue automatically once you're logged in.\n")

    await page.goto("https://www.facebook.com/login", wait_until="domcontentloaded")

    await page.wait_for_url("https://www.facebook.com/", timeout=120_000)
    print("Logged in successfully!")
    await save_session(context)


async def extract_posts_from_page(page: Page, scroll_rounds: int = 5) -> list[dict]:
    posts = []
    seen_texts = set()

    for round_num in range(scroll_rounds):
        print(f"Scroll round {round_num + 1}/{scroll_rounds}...")
        await slow_scroll(page, steps=6)
        await human_delay(1000, 2000)

        #multiple selectors - facebook supposedly changes them often
        selectors = [
            'div[role="article"] div[role="article"]',
            'div[data-pagelet^="FeedUnit"]',
            'div[data-testid="fbfeed_story"]',
            'div[aria-posinset]',
        ]

        article_elements = []
        for selector in selectors:
            elements = await page.query_selector_all(selector)
            if elements:
                print(f"Selector '{selector}' matched {len(elements)} elements")
                for i, el in enumerate(elements):
                    text = await el.inner_text()
                    print(f"Article {i}: {len(text)} chars, preview: {text[:100]!r}")
                article_elements = elements
                break

        if not article_elements:
            print("No post elements found with any selector — dumping page structure...")
            debug = await page.evaluate("""
                () => [...document.querySelectorAll('div[role]')]
                    .slice(0, 20)
                    .map(el => el.getAttribute('role') + ' | ' + (el.getAttribute('data-pagelet') || '') + ' | ' + el.className.slice(0, 60))
            """)
            for line in debug:
                print("   ", line)
            continue

#Look here - to change how authors are fetched and displayed later!!
        for article in article_elements:
            try:
                author = "Unknown"

                for sel in ["strong > span", "strong a",
                            "span[dir=\'auto\'] > a[role=\'link\']:not([aria-label])"]:
                    els = await article.query_selector_all(sel)
                    for el in els:
                        candidate = (await el.inner_text()).strip()
                        if (candidate and 2 < len(candidate) < 60
                                and "/" not in candidate
                                and "facebook" not in candidate.lower()
                                and "\n" not in candidate):
                            author = candidate
                            break
                    if author != "Unknown":
                        break

                if author == "Unknown":
                    candidates = await article.evaluate("""
                        el => [...el.querySelectorAll('a[role="link"]')]
                            .map(a => a.innerText.trim())
                            .filter(t => t.length > 2 && t.length < 60
                                      && !t.includes('/')
                                      && !t.toLowerCase().includes('facebook'))
                    """)
                    if len(candidates) >= 2:
                        author = candidates[1]
                    elif len(candidates) == 1:
                        author = candidates[0]

                timestamp = ""
                for sel in ["abbr[data-utime]", "a[role=\'link\'] abbr", "span abbr"]:
                    el = await article.query_selector(sel)
                    if el:
                        timestamp = (await el.get_attribute("title") or
                                     await el.inner_text() or "").strip()
                        if timestamp:
                            break

                raw_text = await article.inner_text()
                lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]

                skip_exact = {"like", "comment", "share", "reply", "see more",
                              "view", "rate this translation", "\u00b7 rate this translation"}
                lines = [
                    ln for ln in lines
                    if len(ln) > 15
                    and ln.lower() not in skip_exact
                    and not ln.lower().startswith("\u00b7 ")
                    and not ln.isdigit()
                ]

                while lines and lines[0] == author:
                    lines = lines[1:]

                if not lines:
                    continue

                post_text = "\n".join(lines[:30])
                fingerprint = post_text[:80]
                if fingerprint in seen_texts:
                    continue
                seen_texts.add(fingerprint)

                posts.append({
                    "author":     author,
                    "timestamp":  timestamp,
                    "text":       post_text,
                    "source_url": page.url,
                    "scraped_at": datetime.utcnow().isoformat(),
                })
            except Exception as e:
                print(f" post parse error: {e}")
                continue

    print(f"Found {len(posts)} posts on this page.")
    return posts


async def scrape_source(page: Page, source: dict) -> list[dict]:
    url = source["url"]
    label = source.get("label", url)
    print(f"\nScraping: {label} ({url})")

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        await human_delay(2000, 4000)
        posts = await extract_posts_from_page(page, scroll_rounds=source.get("scroll_rounds", 5))
        for p in posts:
            p["source_label"] = label
            p["source_type"] = source.get("type", "unknown")
        return posts
    except Exception as e:
        print(f"Error scraping {label}: {e}")
        return []


async def run_scraper(config: Config, db: Database):
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,  # Keep visible
            args=["--disable-blink-features=AutomationControlled"],
        )

        # Load saved session
        if SESSION_FILE.exists():
            print("Loading saved session...")
            context = await browser.new_context(storage_state=str(SESSION_FILE))
        else:
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
            )

        page = await context.new_page()

        if SESSION_FILE.exists():
            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
            await human_delay(1500, 3000)
            if "login" in page.url.lower():
                print("Session expired. Re-authenticating...")
                await login_flow(page, context)
        else:
            await login_flow(page, context)

        all_posts = []
        for source in config.sources:
            posts = await scrape_source(page, source)
            all_posts.extend(posts)
            await human_delay(2000, 5000)

        await browser.close()

    new_count = db.insert_posts(all_posts)
    print(f"\n✅ Done. {new_count} new posts saved (out of {len(all_posts)} scraped).")
    return new_count
