"""Daily VC reading newsletter — one never-repeated essay per author, emailed.

  python -m newsletter.main             # build + send (respects once-per-day)
  python -m newsletter.main --dry-run   # no send; writes data/preview.html
  python -m newsletter.main --force     # send even if already sent today

Rotation: each author's essays are sent in order, never repeating, until the
list is exhausted, then it recycles. State (sent URLs + last_sent_date) lives in
data/state.json and is committed back by CI so it persists.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from anthropic import Anthropic

from . import authors, deliver, fetch, render, summarize

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
                    stream=sys.stdout)
log = logging.getLogger("newsletter")

STATE_FILE = Path(__file__).parent / "data" / "state.json"


def _load() -> Dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, ValueError):
        return {}


def _save(state: Dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def select(state: Dict) -> List[Dict]:
    """One not-yet-sent essay per author (in order); recycle when exhausted."""
    sent = state.setdefault("sent", {})
    picks = []
    for a in authors.AUTHORS:
        seen = set(sent.get(a["key"], []))
        nxt = next((e for e in a["essays"] if e["url"] not in seen), None)
        if nxt is None:  # whole archive read — start over
            log.info("%s fully read — recycling from the top.", a["name"])
            sent[a["key"]] = []
            nxt = a["essays"][0]
        sent.setdefault(a["key"], [])
        sent[a["key"]].append(nxt["url"])
        log.info("%s: %s", a["name"], nxt["title"])
        picks.append({"author": a, "entry": nxt})
    return picks


def build(picks: List[Dict], client: Optional[Anthropic]) -> List[Dict]:
    issue = []
    for p in picks:
        a, e = p["author"], p["entry"]
        text = fetch.fetch_text(a, e["url"])
        summ = summarize.summarize(a["name"], e["title"], text, e["url"], client=client)
        issue.append({"author": a["name"], "title": e["title"], "url": e["url"], **summ})
    return issue


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    state = _load()

    if not args.dry_run:
        log.info("Preflight: ANTHROPIC=%s | GMAIL=%s | RESEND=%s | to=%s",
                 "SET" if os.getenv("ANTHROPIC_API_KEY") else "MISSING",
                 "SET" if (os.getenv("GMAIL_ADDRESS") and os.getenv("GMAIL_APP_PASSWORD")) else "MISSING",
                 "SET" if os.getenv("RESEND_API_KEY") else "off", deliver.recipient())
        if not args.force and state.get("last_sent_date") == today:
            log.info("Already sent today (%s) — nothing to do.", today)
            return 0

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY")) if os.getenv("ANTHROPIC_API_KEY") else None
    if client is None:
        log.warning("ANTHROPIC_API_KEY not set — takeaways will be placeholders.")

    # Select first so rotation only advances when we actually intend to send.
    picks = select(state)
    issue = build(picks, client)
    date_str = datetime.now().strftime("%A, %B %d, %Y")
    html_body, text_body = render.render_html(issue, date_str), render.render_text(issue, date_str)
    subject = f"📚 The VC Reading Room — {datetime.now().strftime('%b %d')}"

    if args.dry_run:
        out = STATE_FILE.parent / "preview.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html_body)
        print("\n" + text_body)
        log.info("Dry run complete. Preview at %s", out)
        return 0

    if not deliver.send_newsletter(subject, html_body, text_body):
        log.error("Email FAILED — not advancing rotation; the next run will retry.")
        return 1  # don't save state -> no essays consumed, no day marked

    state["last_sent_date"] = today
    _save(state)
    log.info("Done — emailed %d essays.", len(issue))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
