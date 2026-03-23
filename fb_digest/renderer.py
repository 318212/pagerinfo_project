"""
fb_digest/renderer.py
Renders scraped posts into a clean, readable HTML file.(didn't have any better idea for a name)
"""

from datetime import datetime
from pathlib import Path

from database import Database


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FB Digest — {date}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;500&display=swap');

  :root {{
    --bg:         #0f0f0f;
    --surface:    #181818;
    --border:     #2a2a2a;
    --accent:     #c8a96e;
    --text:       #e0ddd5;
    --muted:      #666;
    --author:     #c8a96e;
    --tag-bg:     #1e1a14;
    --tag-text:   #c8a96e;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Lora', Georgia, serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.75;
    padding: 2rem 1rem 6rem;
  }}

  header {{
    max-width: 720px;
    margin: 0 auto 3rem;
    border-bottom: 1px solid var(--border);
    padding-bottom: 1.5rem;
  }}

  header h1 {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    font-weight: 500;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 0.4rem;
  }}

  header .meta {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--muted);
  }}

  .stats {{
    max-width: 720px;
    margin: 0 auto 2rem;
    display: flex;
    gap: 2rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--muted);
  }}

  .stats span {{ color: var(--accent); font-weight: 500; }}

  .post {{
    max-width: 720px;
    margin: 0 auto 1.5rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1.25rem 1.5rem;
    transition: border-color 0.15s;
  }}

  .post:hover {{ border-color: #3d3d3d; }}

  .post-header {{
    display: flex;
    align-items: baseline;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
    flex-wrap: wrap;
  }}

  .author {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--author);
  }}

  .source-tag {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    background: var(--tag-bg);
    color: var(--tag-text);
    border: 1px solid var(--border);
    padding: 0.1em 0.5em;
    border-radius: 2px;
    letter-spacing: 0.05em;
  }}

  .timestamp {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--muted);
    margin-left: auto;
  }}

  .post-text {{
    font-size: 0.95rem;
    white-space: pre-wrap;
    word-break: break-word;
    color: var(--text);
  }}

  .divider {{
    max-width: 720px;
    margin: 2.5rem auto;
    border: none;
    border-top: 1px solid var(--border);
  }}

  .section-label {{
    max-width: 720px;
    margin: 0 auto 1.25rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
  }}

  footer {{
    max-width: 720px;
    margin: 4rem auto 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: var(--muted);
    text-align: center;
  }}
</style>
</head>
<body>

<header>
  <h1>Facebook Digest</h1>
  <div class="meta">Generated {date} · {count} posts</div>
</header>

<div class="stats">
  <div>{count} posts in this digest</div>
  <div>Sources: <span>{sources}</span></div>
</div>

{posts_html}

<footer>fb_digest · personal use only · {date}</footer>
</body>
</html>"""


POST_TEMPLATE = """
<article class="post">
  <div class="post-header">
    <span class="author">{author}</span>
    <span class="source-tag">{source_label}</span>
    <span class="timestamp">{scraped_at}</span>
  </div>
  <div class="post-text">{text}</div>
</article>
"""


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
    )


def render_digest(db: Database, output_dir: str = "output", max_posts: int = 100, min_length: int = 30) -> Path:
    posts = db.get_unread_posts(limit=max_posts, min_length=min_length)

    if not posts:
        print("No unread posts to render.")
        return None

    sources = sorted({p["source_label"] for p in posts if p["source_label"]})
    sources_str = ", ".join(sources) if sources else "—"

    posts_html_parts = []
    current_source = None

    for post in posts:
        # Group by source
        if post["source_label"] != current_source:
            current_source = post["source_label"]
            posts_html_parts.append(
                f'<hr class="divider">\n'
                f'<div class="section-label">{_escape(current_source or "unknown")}</div>'
            )

        timestamp = post["scraped_at"][:16].replace("T", " ") if post["scraped_at"] else ""
        posts_html_parts.append(
            POST_TEMPLATE.format(
                author=_escape(post["author"] or "—"),
                source_label=_escape(post["source_label"] or ""),
                scraped_at=timestamp,
                text=_escape(post["text"]),
            )
        )

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = HTML_TEMPLATE.format(
        date=now,
        count=len(posts),
        sources=_escape(sources_str),
        posts_html="\n".join(posts_html_parts),
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    filename = output_path / f"digest_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
    filename.write_text(html, encoding="utf-8")

    print(f"Digest written to: {filename}")
    return filename
