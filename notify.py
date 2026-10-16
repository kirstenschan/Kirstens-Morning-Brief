"""
Send the morning recap to your phone through ntfy (https://ntfy.sh).

Set NTFY_TOPIC to the private topic name you subscribed to in the ntfy app.
Anyone who knows the name can read the messages, so use a long, random one.
"""

import json
import os
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo


def format_message(recap: dict) -> str:
    lines = [recap["quick_take"]]
    for i, s in enumerate(recap["standouts"], 1):
        lines.append(f"\n{i}. {s['title']} ({s['publisher']})\n→ {s['why']}")
    return "\n".join(lines)


def send_recap(topic: dict, settings: dict, recap: dict) -> None:
    ntfy_topic = os.environ.get("NTFY_TOPIC")
    message = format_message(recap)
    today = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%a %b %-d")
    title = f"{topic['name']} · {today}"

    if not ntfy_topic:
        print(f"  (NTFY_TOPIC not set; this is what would be sent)\n--- {title} ---\n{message}\n---")
        return

    payload = {
        "topic": ntfy_topic,
        "title": title,
        "message": message,
        "tags": ["newspaper"],
        # A "Read" button for each stand-out story (ntfy allows up to 3)
        "actions": [
            {"action": "view", "label": f"Read #{i}", "url": s["link"], "clear": False}
            for i, s in enumerate(recap["standouts"][:3], 1)
            if s.get("link")
        ],
    }
    if settings.get("dashboard_url"):
        # Tapping the notification itself opens the dashboard on this topic's tab
        payload["click"] = f"{settings['dashboard_url'].rstrip('/')}/#{topic['slug']}"

    request = urllib.request.Request(
        "https://ntfy.sh",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            print(f"  Push sent ({response.status})")
    except Exception as err:
        print(f"  ! Push failed: {err}")
