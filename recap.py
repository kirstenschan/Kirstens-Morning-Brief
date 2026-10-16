"""
Morning recap: pick the stand-out new stories and explain why they matter.

With an ANTHROPIC_API_KEY set, Claude writes a short take on the day and a
one-line "why it matters" for each stand-out. Without one (or if the AI call
fails), a basic recap is built from simple rules so the morning push still arrives.
"""

import json
import os
import re


def score(story: dict, topic: dict) -> int:
    """Rough 'stand-out' score: trusted source, picked up by several feeds, touches several themes."""
    points = 0
    if any(src in topic["priority_sources"] for src in story["seen_in"]):
        points += 3
    points += len(story["seen_in"]) - 1
    points += len([t for t in story["themes"] if t != "Other"])
    return points


def basic_recap(topic: dict, settings: dict, ranked: list[dict]) -> dict:
    top = ranked[: settings.get("recap_top_stories", 3)]
    return {
        "written_by": "rules",
        "quick_take": f"{len(ranked)} new {topic['name']} stor{'y' if len(ranked) == 1 else 'ies'} since yesterday.",
        "standouts": [
            {**pick(s), "why": "Themes: " + ", ".join(s["themes"])} for s in top
        ],
    }


def pick(story: dict) -> dict:
    return {k: story[k] for k in ("id", "title", "publisher", "link")}


def ai_recap(topic: dict, settings: dict, ranked: list[dict]) -> dict:
    import anthropic  # only needed when an API key is set

    candidates = ranked[:15]
    listing = "\n".join(
        f"[{s['id']}] {s['title']} ({s['publisher']}) | themes: {', '.join(s['themes'])} | {s['snippet']}"
        for s in candidates
    )
    n = settings.get("recap_top_stories", 3)

    prompt = f"""You write a short morning news recap that will be read as a phone notification.

Reader: {settings['reader_profile'].strip()}
Topic: {topic['name']} - {topic.get('recap_focus', '').strip()}

New stories since yesterday (id in brackets):
{listing}

Pick the {n} most important stories for this reader. Prefer substance (regulator actions, firm-wide changes, shifts in what entry-level staff do) over press-release fluff, and avoid picking two stories about the same event.

Reply with JSON only, no other text:
{{"quick_take": "1-2 plain sentences on the overall picture today, under 220 characters",
  "standouts": [{{"id": "story id", "why": "one sentence, under 140 characters, on why it matters to this reader"}}]}}

Base everything only on the headlines and snippets above; do not invent details."""

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    response = client.messages.create(
        model=settings.get("recap_model", "claude-sonnet-5-5"),
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    parsed = json.loads(re.search(r"\{.*\}", text, re.S).group(0))

    by_id = {s["id"]: s for s in candidates}
    standouts = [
        {**pick(by_id[item["id"]]), "why": item["why"]}
        for item in parsed["standouts"]
        if item.get("id") in by_id
    ][:n]
    if not standouts:
        raise ValueError("AI reply did not reference any real story ids")

    return {"written_by": "ai", "quick_take": parsed["quick_take"], "standouts": standouts}


def build_recap(topic: dict, settings: dict, new_stories: list[dict]) -> dict:
    if not new_stories:
        return {"written_by": "rules", "quick_take": f"No new {topic['name']} stories since yesterday.", "standouts": []}

    ranked = sorted(new_stories, key=lambda s: score(s, topic), reverse=True)

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return ai_recap(topic, settings, ranked)
        except Exception as err:  # keep the morning push working even if the AI call fails
            print(f"  ! AI recap failed ({err}); using basic recap instead")
    return basic_recap(topic, settings, ranked)
