"""
fb_digest/main.py
CLI entry point for the Facebook Digest scraper.

Usage:
    python main.py scrape          — scrape all configured sources
    python main.py digest          — render unread posts to HTML
    python main.py run             — scrape + digest in one go
    python main.py stats           — show database stats
    python main.py mark-read       — mark all current posts as read
    python main.py reset-session   — delete saved login session
"""

import asyncio
import sys
from pathlib import Path


def _load_deps():
    try:
        from config import Config
        from database import Database
        from scraper import run_scraper
        from renderer import render_digest
        return Config, Database, run_scraper, render_digest
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("   Run:  pip install -r requirements.txt")
        print("         playwright install chromium")
        sys.exit(1)


def cmd_scrape():
    Config, Database, run_scraper, _ = _load_deps()
    config = Config.load()
    db = Database()
    asyncio.run(run_scraper(config, db))


def cmd_digest():
    Config, Database, _, render_digest = _load_deps()
    config = Config.load()
    db = Database()
    path = render_digest(db, output_dir=config.output_dir,
                         max_posts=config.max_posts_per_digest,
                         min_length=config.min_post_length)
    if path:
        db.mark_all_read()
        print(f"Marked {path.name} posts as read.")
        import webbrowser
        webbrowser.open(path.resolve().as_uri())

# order in the pipeline:
# scrape > digest > open
def cmd_run():
    Config, Database, run_scraper, render_digest = _load_deps()
    config = Config.load()
    db = Database()
    asyncio.run(run_scraper(config, db))
    path = render_digest(db, output_dir=config.output_dir,
                         max_posts=config.max_posts_per_digest,
                         min_length=config.min_post_length)
    if path:
        db.mark_all_read()
        import webbrowser
        webbrowser.open(path.resolve().as_uri())


def cmd_stats():
    _, Database, _, _ = _load_deps()
    db = Database()
    s = db.stats()
    print(f"\n Database Stats")
    print(f"   Total posts : {s['total']}")
    print(f"   Unread      : {s['unread']}")
    print(f"\n   Posts by source:")
    for row in s["sources"]:
        print(f"     {row['source_label'] or '(unknown)':40s} {row['cnt']:>4} posts")
    print()


def cmd_mark_read():
    _, Database, _, _ = _load_deps()
    db = Database()
    db.mark_all_read()
    print("All posts marked as read.")


def cmd_reset_session():
    session_file = Path("data/session.json")
    if session_file.exists():
        session_file.unlink()
        print("Session deleted. You'll be prompted to log in next run.")
    else:
        print("No session file found.")


COMMANDS = {
    "scrape":        cmd_scrape,
    "digest":        cmd_digest,
    "run":           cmd_run,
    "stats":         cmd_stats,
    "mark-read":     cmd_mark_read,
    "reset-session": cmd_reset_session,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        print("Available commands:", ", ".join(COMMANDS))
        sys.exit(0)
    COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    main()
