"""
fb_digest/config.py
Loads and validates the user's configuration from config.yaml.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml


@dataclass
class Config:
    sources: list[dict] = field(default_factory=list)
    output_dir: str = "output"
    max_posts_per_digest: int = 100
    min_post_length: int = 1  # ignore short posts (idiotic, swap to int=1 or remove that property fully)

    @classmethod
    def load(cls, path: str = "config.yaml") -> "Config":
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {path}\n"
                "Copy config.example.yaml to config.yaml and edit it."
            )
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        sources = []
        for s in data.get("sources", []):
            if isinstance(s, str):
                sources.append({"url": s, "label": s, "type": "unknown", "scroll_rounds": 5})
            else:
                sources.append({
                    "url": s["url"],
                    "label": s.get("label", s["url"]),
                    "type": s.get("type", "unknown"),  
                    "scroll_rounds": s.get("scroll_rounds", 5),
                })

        return cls(
            sources=sources,
            output_dir=data.get("output_dir", "output"),
            max_posts_per_digest=data.get("max_posts_per_digest", 100),
            min_post_length=data.get("min_post_length", 30),
        )
