"""
Daily job. For every topic file in topics/:
  1. pull news from Google News RSS feeds
  2. keep stories that match the topic's keywords, tag them by theme
  3. write a morning recap (AI-written if an API key is set)
  4. save everything to data/ for the dashboard
  5. send the recap to your phone (if a notification topic is set)

Run locally:   python fetch_news.py
Test offline:  python fetch_news.py --feed-file sample_feed.xml --no-notify
"""

import argparse
import hashlib
import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote_plus

import feedparser
import yaml

from notify import send_recap
from recap import build_recap

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
TOPICS_DIR = ROOT / "topics"


# ---------- loading settings ----------

def load_settings() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text())


def load_topics() -> list[dict]:
    """Every topics/*.yaml file except ones starting with '_' (like the template)."""
    topics = []
    for path in sorted(TOPICS_DIR.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        topic = yaml.safe_load(path.read_text())
        topic["slug"] = path.stem
        topic.setdefault("notify", True)
        topic.setdefault("priority_sources", [])
        topic.setdefault("themes", {})
        topics.append(topic)
    return topics


# ---------- helpers ----------

def google_news_url(query: str) -> str:
    """Turn a search query into a Google News RSS feed URL (last 7 days, US English)."""
    q = quote_plus(f"{query} when:7d")
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def clean(text: str) -> str:
    """Strip HTML tags and extra whitespace from feed text."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def mentions_any(text: str, terms: list[str]) -> bool:
    padded = f" {text.lower()} "
    return any(term.lower() in padded for term in terms)


def story_id(title: str) -> str:
    """Same headline from two feeds -> same id, so duplicates collapse."""
    key = re.sub(r"[^a-z0-9]", "", title.lower())[:80]
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def parse_entry(entry, source_name: str) -> dict:
    title = clean(entry.get("title", ""))
    publisher = ""
    # Google News titles look like "Headline - Publisher"
    if " - " in title:
        title, publisher = title.rsplit(" - ", 1)
    publisher = publisher or entry.get("source", {}).get("title", "") or source_name

    published = entry.get("published_parsed") or entry.get("updated_parsed")
    when = (
        datetime(*published[:6], tzinfo=timezone.utc)
        if published
        else datetime.now(timezone.utc)
    )
    return {
        "id": story_id(title),
        "title": title,
        "publisher": publisher,
        "seen_in": [source_name],
        "link": entry.get("link", ""),
        "snippet": clean(entry.get("summary", ""))[:280],
        "published": when.isoformat(),
    }


# ---------- one topic ----------

def update_topic(topic: dict, settings: dict, run_time: datetime, feed_file: str | None) -> dict:
    print(f"\n== {topic['name']} ==")
    data_path = DATA_DIR / f"{topic['slug']}.json"
    old = json.loads(data_path.read_text()) if data_path.exists() else {}
    stories = {s["id"]: s for s in old.get("stories", [])}

    if feed_file:
        feeds = [("Sample", feed_file)]
    else:
        feeds = [(s["name"], google_news_url(s["query"])) for s in topic["sources"]]

    new_ids = set()
    for source_name, url in feeds:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            print(f"  ! {source_name}: could not read feed ({feed.bozo_exception})")
            continue

        kept = 0
        for entry in feed.entries:
            story = parse_entry(entry, source_name)
            text = f"{story['title']} {story['snippet']}"
            if not all(mentions_any(text, group) for group in topic["must_mention"]):
                continue

            existing = stories.get(story["id"])
            if existing:
                # Seen before (earlier run or another feed today): note the extra source
                if source_name not in existing["seen_in"]:
                    existing["seen_in"].append(source_name)
                continue

            story["themes"] = [n for n, words in topic["themes"].items() if mentions_any(text, words)] or ["Other"]
            story["first_seen"] = run_time.isoformat()
            stories[story["id"]] = story
            new_ids.add(story["id"])
            kept += 1
        print(f"  {source_name}: {len(feed.entries)} items, {kept} new")

    # Drop anything older than keep_days
    cutoff = run_time - timedelta(days=settings.get("keep_days", 30))
    stories = {k: s for k, s in stories.items() if datetime.fromisoformat(s["published"]) >= cutoff}
    ordered = sorted(stories.values(), key=lambda s: s["published"], reverse=True)

    new_stories = [s for s in ordered if s["id"] in new_ids]
    recap = build_recap(topic, settings, new_stories)

    DATA_DIR.mkdir(exist_ok=True)
    data_path.write_text(json.dumps({
        "name": topic["name"],
        "updated": run_time.isoformat(),
        "themes": list(topic["themes"].keys()) + ["Other"],
        "recap": recap,
        "stories": ordered,
    }, indent=2))

    print(f"  -> {len(new_stories)} new, {len(ordered)} total. Recap written by: {recap['written_by']}")
    return {"slug": topic["slug"], "name": topic["name"], "new_count": len(new_stories), "recap": recap}


# ---------- main ----------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--feed-file", help="Parse this local RSS file instead of the web (for testing)")
    parser.add_argument("--no-notify", action="store_true", help="Don't send phone notifications")
    args = parser.parse_args()

    settings = load_settings()
    topics = load_topics()
    run_time = datetime.now(timezone.utc)

    results = []
    for topic in topics:
        result = update_topic(topic, settings, run_time, args.feed_file)
        results.append(result)
        if topic["notify"] and not args.no_notify:
            send_recap(topic, settings, result["recap"])

    # Index of topics, used by the dashboard to build its tabs
    (DATA_DIR / "topics.json").write_text(json.dumps({
        "updated": run_time.isoformat(),
        "topics": [{"slug": r["slug"], "name": r["name"], "new_count": r["new_count"]} for r in results],
    }, indent=2))
    print("\nAll topics done.")


if __name__ == "__main__":
    main()
