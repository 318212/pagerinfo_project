"""
pagerinfo/api.py
Flask API — serves scraped posts as JSON and hosts the PWA frontend.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, render_template

app = Flask(__name__, static_folder="static", template_folder="templates")

DB_PATH = Path(__file__).parent.parent / "fb_digest" / "data" / "digest.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json")

@app.route("/sw.js")
def service_worker():
    return send_from_directory("static/js", "sw.js",
                               mimetype="application/javascript")



@app.route("/api/posts")
def get_posts():
    """
    GET /api/posts
    Query params:
      - limit  (default 60)
      - unread (default false — set to 'true' for unread only)
      - source (filter by source_label)
    """
    limit  = int(request.args.get("limit", 60))
    unread = request.args.get("unread", "false").lower() == "true"
    source = request.args.get("source", None)

    query  = "SELECT * FROM posts WHERE 1=1"
    params = []

    if unread:
        query += " AND read = 0"
    if source:
        query += " AND source_label = ?"
        params.append(source)

    query += " ORDER BY scraped_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()

    posts = [dict(row) for row in rows]
    return jsonify({"posts": posts, "count": len(posts)})


@app.route("/api/posts/<int:post_id>/read", methods=["POST"])
def mark_post_read(post_id):
    with get_db() as conn:
        conn.execute("UPDATE posts SET read = 1 WHERE id = ?", (post_id,))
    return jsonify({"ok": True})


@app.route("/api/posts/mark-all-read", methods=["POST"])
def mark_all_read():
    with get_db() as conn:
        conn.execute("UPDATE posts SET read = 1 WHERE read = 0")
    return jsonify({"ok": True})


@app.route("/api/sources")
def get_sources():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT source_label, source_type, COUNT(*) as count "
            "FROM posts GROUP BY source_label ORDER BY count DESC"
        ).fetchall()
    return jsonify({"sources": [dict(r) for r in rows]})


@app.route("/api/stats")
def get_stats():
    with get_db() as conn:
        total  = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        unread = conn.execute("SELECT COUNT(*) FROM posts WHERE read=0").fetchone()[0]
        last   = conn.execute(
            "SELECT scraped_at FROM posts ORDER BY scraped_at DESC LIMIT 1"
        ).fetchone()
    return jsonify({
        "total":        total,
        "unread":       unread,
        "last_scraped": last[0] if last else None,
    })


#VAPID - push notifications
SUBS_FILE = Path(__file__).parent.parent / "fb_digest" / "data" / "subscriptions.json"

def load_subs():
    if SUBS_FILE.exists():
        return json.loads(SUBS_FILE.read_text())
    return []

def save_subs(subs):
    SUBS_FILE.write_text(json.dumps(subs, indent=2))

@app.route("/api/push/subscribe", methods=["POST"])
def push_subscribe():
    sub = request.get_json()
    subs = load_subs()
    endpoints = [s["endpoint"] for s in subs]
    if sub["endpoint"] not in endpoints:
        subs.append(sub)
        save_subs(subs)
    return jsonify({"ok": True})

@app.route("/api/push/unsubscribe", methods=["POST"])
def push_unsubscribe():
    sub = request.get_json()
    subs = [s for s in load_subs() if s["endpoint"] != sub["endpoint"]]
    save_subs(subs)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
