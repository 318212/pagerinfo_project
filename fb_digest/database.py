"""
fb_digest/database.py
SQLite storage with built-in deduplication (in case we scrape the same post multiple times) using content hashing.
"""

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path


DB_PATH = Path("data/digest.db")


class Database:
    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS posts (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    hash           TEXT    UNIQUE NOT NULL,
                    author         TEXT,
                    post_timestamp TEXT,
                    text           TEXT    NOT NULL,
                    source_url     TEXT,
                    source_label   TEXT,
                    source_type    TEXT,
                    scraped_at     TEXT,
                    read           INTEGER DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_hash       ON posts(hash);
                CREATE INDEX IF NOT EXISTS idx_scraped_at ON posts(scraped_at);
                CREATE INDEX IF NOT EXISTS idx_read       ON posts(read);
            """)

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text[:200].encode()).hexdigest()

    def insert_posts(self, posts: list[dict]) -> int:
        new_count = 0
        with self._connect() as conn:
            for post in posts:
                h = self._hash(post["text"])
                try:
                    conn.execute(
                        """
                        INSERT INTO posts (hash, author, post_timestamp, text, source_url, source_label, source_type, scraped_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            h,
                            post.get("author", ""),
                            post.get("timestamp", ""),
                            post["text"],
                            post.get("source_url", ""),
                            post.get("source_label", ""),
                            post.get("source_type", ""),
                            post.get("scraped_at", datetime.utcnow().isoformat()),
                        ),
                    )
                    new_count += 1
                except sqlite3.IntegrityError:
                    pass  
        return new_count

    def get_unread_posts(self, limit: int = 100, min_length: int = 30) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT * FROM posts
                WHERE read = 0 AND length(text) >= ?
                ORDER BY scraped_at DESC
                LIMIT ?
                """,
                (min_length, limit),
            ).fetchall()

    def get_all_posts(self, limit: int = 200) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM posts ORDER BY scraped_at DESC LIMIT ?",
                (limit,),
            ).fetchall()

    def mark_all_read(self):
        with self._connect() as conn:
            conn.execute("UPDATE posts SET read = 1 WHERE read = 0")

    def mark_read(self, post_id: int):
        with self._connect() as conn:
            conn.execute("UPDATE posts SET read = 1 WHERE id = ?", (post_id,))

    def stats(self) -> dict:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
            unread = conn.execute("SELECT COUNT(*) FROM posts WHERE read = 0").fetchone()[0]
            sources = conn.execute(
                "SELECT source_label, COUNT(*) as cnt FROM posts GROUP BY source_label ORDER BY cnt DESC"
            ).fetchall()
        return {"total": total, "unread": unread, "sources": sources}
