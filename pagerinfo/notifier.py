"""
Notification system for mobile devices (will be available in version1.0)
pagerinfo/notifier.py
Sends Web Push notifications to all subscribed devices when new posts arrive.
Uses VAPID (Voluntary Application Server Identification).
"""

import asyncio
import json
import os
from pathlib import Path

SUBS_FILE   = Path("data/subscriptions.json")
VAPID_FILE  = Path("data/vapid_keys.json")

#Work on this will be conducted for version 1 (see roadmap)
VAPID_CONTACT = os.environ.get("VAPID_CONTACT", "mailto:test@example.com")


def load_vapid_keys() -> dict | None:
    if VAPID_FILE.exists():
        return json.loads(VAPID_FILE.read_text())
    return None


async def send_push_notifications(new_count: int):
    """Send a push notification to all subscribed devices."""
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        print("pywebpush not installed — skipping push notifications.")
        print("Run: pip install pywebpush")
        return

    vapid = load_vapid_keys()
    if not vapid:
        print("No VAPID keys found. Run: python setup_vapid.py")
        return

    subs = json.loads(SUBS_FILE.read_text()) if SUBS_FILE.exists() else []
    if not subs:
        return

    payload = json.dumps({
        "title": "PagerInfo",
        "body":  f"{new_count} new post{'s' if new_count > 1 else ''} arrived",
        "icon":  "/static/icons/icon-192.png",
        "badge": "/static/icons/badge-72.png",
        "url":   "/",
    })

    dead = []
    for sub in subs:
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=vapid["private_key"],
                vapid_claims={"sub": VAPID_CONTACT},
            )
        except WebPushException as e:
            if "410" in str(e) or "404" in str(e):
                dead.append(sub["endpoint"]) 
            else:
                print(f"Push error: {e}")

    # Clean up expired subscriptions
    if dead:
        subs = [s for s in subs if s["endpoint"] not in dead]
        SUBS_FILE.write_text(json.dumps(subs, indent=2))
