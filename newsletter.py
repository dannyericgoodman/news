"""Daily VC reading newsletter — one never-repeated essay per author, emailed.

Single-file build. Run:
  python newsletter.py            # build + send (once per day)
  python newsletter.py --dry-run  # no send; writes data/preview.html
  python newsletter.py --force    # send even if already sent today

ADD/REMOVE AUTHORS: edit the AUTHORS list below. Each author needs a unique
`key`, display `name`, fetch `kind` ("pg" = plain HTML like paulgraham.com,
"wp" = WordPress + an `api_url`), and an ordered `essays` list of {title, url}.
Essays are sent in order, never repeating, until exhausted, then recycle.
"""

import argparse
import html
import json
import logging
import os
import re
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from anthropic import Anthropic

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
                    stream=sys.stdout)
log = logging.getLogger("newsletter")

STATE_FILE = Path(__file__).parent / "data" / "state.json"

# ===========================================================================
# AUTHORS — edit this list to add/remove authors.
# ===========================================================================
AUTHORS = [
    {
        "key": "paul_graham", "name": "Paul Graham", "kind": "pg",
        "essays": [
            {"title": "Startup = Growth", "url": "https://paulgraham.com/growth.html"},
            {"title": "Do Things that Don't Scale", "url": "https://paulgraham.com/ds.html"},
            {"title": "How to Get Startup Ideas", "url": "https://paulgraham.com/startupideas.html"},
            {"title": "What We Look for in Founders", "url": "https://paulgraham.com/founders.html"},
            {"title": "Black Swan Farming", "url": "https://paulgraham.com/swan.html"},
            {"title": "How to Convince Investors", "url": "https://paulgraham.com/convince.html"},
            {"title": "The 18 Mistakes That Kill Startups", "url": "https://paulgraham.com/startupmistakes.html"},
            {"title": "How to Make Wealth", "url": "https://paulgraham.com/wealth.html"},
            {"title": "Relentlessly Resourceful", "url": "https://paulgraham.com/relres.html"},
            {"title": "Startups in 13 Sentences", "url": "https://paulgraham.com/13sentences.html"},
            {"title": "Default Alive or Default Dead?", "url": "https://paulgraham.com/aord.html"},
            {"title": "The Anatomy of Determination", "url": "https://paulgraham.com/determination.html"},
            {"title": "Maker's Schedule, Manager's Schedule", "url": "https://paulgraham.com/makersschedule.html"},
            {"title": "How to Start a Startup", "url": "https://paulgraham.com/start.html"},
            {"title": "How to Think for Yourself", "url": "https://paulgraham.com/think.html"},
        ],
    },
    {
        "key": "bill_gurley", "name": "Bill Gurley", "kind": "wp",
        "api_url": "https://abovethecrowd.com/wp-json/wp/v2/posts",
        "essays": [
            {"title": "All Markets Are Not Created Equal", "url": "https://abovethecrowd.com/2012/11/13/all-markets-are-not-created-equal-10-factors-to-consider-when-evaluating-digital-marketplaces/"},
            {"title": "All Revenue is Not Created Equal: The Keys to the 10X Revenue Club", "url": "https://abovethecrowd.com/2011/05/24/all-revenue-is-not-created-equal-the-keys-to-the-10x-revenue-club/"},
            {"title": "The Dangerous Seduction of the Lifetime Value (LTV) Formula", "url": "https://abovethecrowd.com/2012/09/04/the-dangerous-seduction-of-the-lifetime-value-ltv-formula/"},
            {"title": "How to Miss By a Mile: An Alternative Look at Uber's Potential Market Size", "url": "https://abovethecrowd.com/2014/07/11/how-to-miss-by-a-mile-an-alternative-look-at-ubers-potential-market-size/"},
            {"title": "Money Out of Nowhere: How Internet Marketplaces Unlock Economic Wealth", "url": "https://abovethecrowd.com/2019/02/27/money-out-of-nowhere-how-internet-marketplaces-unlock-economic-wealth/"},
            {"title": "The Thing I Love Most About Uber", "url": "https://abovethecrowd.com/2018/04/19/the-thing-i-love-most-about-uber/"},
            {"title": "On the Road to Recap", "url": "https://abovethecrowd.com/2016/04/21/on-the-road-to-recap/"},
            {"title": "Why Facebook Clearly Belongs in the 10X Revenue Club", "url": "https://abovethecrowd.com/2012/02/01/why-facebook-clearly-belongs-in-the-10x-revenue-club/"},
        ],
    },
    {
        "key": "andrew_chen", "name": "Andrew Chen", "kind": "wp",
        "api_url": "https://andrewchen.com/wp-json/wp/v2/posts",
        "essays": [
            {"title": "The Law of Shitty Clickthroughs", "url": "https://andrewchen.com/the-law-of-shitty-clickthroughs/"},
            {"title": "Growth Hacker is the new VP Marketing", "url": "https://andrewchen.com/how-to-be-a-growth-hacker-an-airbnbcraigslist-case-study/"},
            {"title": "The Next Feature Fallacy", "url": "https://andrewchen.com/the-next-feature-fallacy-the-fallacy-that-the-next-new-feature-will-suddenly-make-people-use-your-product/"},
            {"title": "New data shows losing 80% of mobile users is normal", "url": "https://andrewchen.com/new-data-shows-why-losing-80-of-your-mobile-users-is-normal-and-that-the-best-apps-do-much-better/"},
            {"title": "Minimize your Time to Product/Market Fit", "url": "https://andrewchen.com/ttpmf-time-to-product-market-fit/"},
            {"title": "Zero to Product/Market Fit", "url": "https://andrewchen.com/zero-to-productmarket-fit-presentation/"},
            {"title": "What to do when growth stalls", "url": "https://andrewchen.com/growth-stalls/"},
        ],
    },
]

# ===========================================================================
# Fetch full text (best effort)
# ===========================================================================
_HEADERS = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"),
            "Accept": "text/html,application/json,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"}


def _get(url, **kw):
    try:
        r = requests.get(url, headers=_HEADERS, timeout=30, **kw)
        if r.status_code == 200:
            return r
        log.warning("GET %s -> HTTP %s", url, r.status_code)
    except requests.RequestException as exc:
        log.warning("GET %s failed: %s", url, exc)
    return None


def fetch_text(author: Dict, url: str) -> Optional[str]:
    try:
        if author.get("kind") == "wp" and author.get("api_url"):
            slug = urlparse(url).path.strip("/").split("/")[-1]
            r = _get(author["api_url"], params={"slug": slug, "_fields": "content"})
            if r:
                try:
                    data = r.json()
                    if isinstance(data, list) and data:
                        txt = BeautifulSoup((data[0].get("content") or {}).get("rendered", ""),
                                            "html.parser").get_text("\n", strip=True)
                        if txt:
                            return txt[:16000]
                except ValueError:
                    pass
        r = _get(url)
        if not r:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        for t in soup(["script", "style", "nav", "footer", "header"]):
            t.decompose()
        root = soup.find("article") or soup.body or soup
        return re.sub(r"\n{3,}", "\n\n", root.get_text("\n", strip=True)).strip()[:16000]
    except Exception as exc:
        log.error("Fetch failed for %s: %s", url, exc)
        return None


# ===========================================================================
# Summarize with Claude (Opus 4.8 -> Sonnet; knowledge fallback if no text)
# ===========================================================================
def _models() -> List[str]:
    chain = ([os.getenv("VC_MODEL")] if os.getenv("VC_MODEL") else []) + \
            ["claude-opus-4-8", "claude-sonnet-4-20250514"]
    out, seen = [], set()
    for m in chain:
        if m and m not in seen:
            seen.add(m); out.append(m)
    return out


_SHAPE = """Respond with ONLY a JSON object in exactly this shape:
{{"one_liner":"<one sentence: the core idea>","takeaways":["<3-5 crisp one-sentence \
takeaways; durable mental models and investor judgment>"],"investor_angle":"<one sentence \
on why this matters for an early-stage VC's decisions or founder evaluation>"}}"""


def summarize(author_name, title, text, client) -> Dict:
    if not os.getenv("ANTHROPIC_API_KEY") and client is None:
        return _fallback(title, "ANTHROPIC_API_KEY not set")
    if text:
        prompt = (f'You are a mentor helping an aspiring elite early-stage VC study the canon. '
                  f'Distill this essay by {author_name}, "{title}", for a busy investor. {_SHAPE}'
                  f'\n\nESSAY:\n---\n{text}\n---')
        mode = "full-text"
    else:
        log.warning("No fetched text for '%s' — summarizing from knowledge.", title)
        prompt = (f'You are a mentor helping an aspiring elite early-stage VC study the canon. '
                  f'Summarize the well-known essay "{title}" by {author_name} from your own '
                  f'knowledge. If you are not confident you know this specific essay, return '
                  f'{{"one_liner":"","takeaways":[],"investor_angle":""}} and nothing else — do '
                  f'NOT fabricate. {_SHAPE}')
        mode = "knowledge"
    client = client or Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    last = None
    for model in _models():
        try:
            resp = client.messages.create(model=model, max_tokens=1024,
                                           messages=[{"role": "user", "content": prompt}])
            raw = re.sub(r"^```(?:json)?|```$", "", resp.content[0].text.strip(), flags=re.MULTILINE).strip()
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            data = json.loads(m.group(0) if m else raw)
            tk = data.get("takeaways") or []
            tk = [tk] if isinstance(tk, str) else tk
            tk = [str(t).strip() for t in tk if str(t).strip()]
            if tk:
                log.info("Summarized '%s' (%s, %s).", title, mode, model)
                return {"one_liner": str(data.get("one_liner", "")).strip(), "takeaways": tk,
                        "investor_angle": str(data.get("investor_angle", "")).strip()}
            last = "empty (not recognized)"
        except Exception as exc:
            last = str(exc); log.warning("Model %s failed for '%s': %s", model, title, exc)
    log.error("Summary failed for '%s': %s", title, last)
    return _fallback(title, "fetch blocked & not recognized" if mode == "knowledge" else "model error")


def _fallback(title, reason) -> Dict:
    return {"one_liner": f"Classic essay: {title}.",
            "takeaways": [f"Auto-summary unavailable ({reason}) — read it via the link below."],
            "investor_angle": "Part of the early-stage VC canon worth reading in full."}


# ===========================================================================
# Render email
# ===========================================================================
def _esc(s):
    return html.escape(s or "")


def render_html(issues, date_str) -> str:
    cards = []
    for it in issues:
        tks = "".join(f"<li style='margin:0 0 6px;line-height:1.5;'>{_esc(t)}</li>" for t in it["takeaways"])
        angle = (f"<p style='margin:14px 0 0;padding:10px 14px;background:#f4f6fb;border-left:3px solid "
                 f"#4a6cf7;border-radius:4px;font-size:14px;color:#33415c;'><strong>Investor angle:&nbsp;</strong>"
                 f"{_esc(it['investor_angle'])}</p>") if it.get("investor_angle") else ""
        cards.append(f"""<tr><td style="padding:0 0 28px;">
          <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="border:1px solid #e6e8ec;border-radius:10px;overflow:hidden;">
            <tr><td style="background:#0f172a;padding:14px 20px;"><span style="color:#93a4c4;font-size:12px;letter-spacing:1px;text-transform:uppercase;">{_esc(it['author'])}</span></td></tr>
            <tr><td style="padding:20px;">
              <a href="{_esc(it['url'])}" style="color:#0f172a;text-decoration:none;font-size:20px;font-weight:700;line-height:1.3;">{_esc(it['title'])}</a>
              <p style="margin:8px 0 16px;color:#52617a;font-style:italic;font-size:15px;line-height:1.5;">{_esc(it['one_liner'])}</p>
              <p style="margin:0 0 8px;font-size:13px;font-weight:700;color:#0f172a;text-transform:uppercase;letter-spacing:0.5px;">Key takeaways</p>
              <ul style="margin:0;padding-left:20px;color:#1f2937;font-size:15px;">{tks}</ul>
              {angle}
              <p style="margin:18px 0 0;"><a href="{_esc(it['url'])}" style="display:inline-block;background:#4a6cf7;color:#fff;text-decoration:none;padding:9px 18px;border-radius:6px;font-size:14px;font-weight:600;">Read the full essay →</a></p>
            </td></tr></table></td></tr>""")
    return (f'<!DOCTYPE html><html><body style="margin:0;padding:0;background:#eef1f6;font-family:-apple-system,'
            f'Segoe UI,Roboto,Helvetica,Arial,sans-serif;"><table width="100%" cellpadding="0" cellspacing="0" '
            f'role="presentation" style="background:#eef1f6;padding:28px 12px;"><tr><td align="center">'
            f'<table width="600" cellpadding="0" cellspacing="0" role="presentation" style="max-width:600px;width:100%;">'
            f'<tr><td style="padding:0 0 22px;text-align:center;"><h1 style="margin:0;font-size:24px;color:#0f172a;">'
            f'The VC Reading Room</h1><p style="margin:6px 0 0;color:#6b7890;font-size:14px;">Daily wisdom from the '
            f'greats · {_esc(date_str)}</p></td></tr>{"".join(cards)}<tr><td style="padding:6px 0 0;text-align:center;'
            f'color:#9aa6bd;font-size:12px;line-height:1.6;">One classic essay each from your chosen investors.<br>'
            f'Study daily. Compound the wisdom.</td></tr></table></td></tr></table></body></html>')


def render_text(issues, date_str) -> str:
    lines = [f"THE VC READING ROOM — {date_str}", "=" * 48, ""]
    for it in issues:
        lines += [f"## {it['author']}: {it['title']}", f"   {it['one_liner']}", "", "   KEY TAKEAWAYS:"]
        lines += [f"   - {t}" for t in it["takeaways"]]
        if it.get("investor_angle"):
            lines.append(f"   INVESTOR ANGLE: {it['investor_angle']}")
        lines += [f"   Read: {it['url']}", "", "-" * 48, ""]
    return "\n".join(lines)


# ===========================================================================
# Deliver (Gmail SMTP — proven; Resend optional)
# ===========================================================================
def _recipient() -> str:
    return (os.getenv("NEWSLETTER_TO") or os.getenv("GMAIL_ADDRESS")
            or "danny.eric.goodman@gmail.com").strip()


def _send_gmail(subject, html_body, text_body) -> bool:
    user = (os.getenv("GMAIL_ADDRESS") or "").strip()
    pw = (os.getenv("GMAIL_APP_PASSWORD") or "").replace(" ", "")
    if not user or not pw:
        return False
    to = _recipient()
    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"], msg["Reply-To"] = subject, f"The VC Reading Room <{user}>", to, user
    msg.attach(MIMEText(text_body, "plain")); msg.attach(MIMEText(html_body, "html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
            s.login(user, pw)
            s.sendmail(user, [r.strip() for r in to.split(",")], msg.as_string())
        log.info("Email sent via Gmail to %s", to)
        return True
    except smtplib.SMTPAuthenticationError as exc:
        log.error("Gmail auth FAILED (need 2FA + a 16-char App Password): %s", exc)
    except Exception as exc:
        log.error("Gmail send FAILED: %s", exc)
    return False


def _send_resend(subject, html_body, text_body) -> bool:
    key = os.getenv("RESEND_API_KEY", "").strip()
    if not key:
        return False
    sender = os.getenv("RESEND_FROM", "The VC Reading Room <onboarding@resend.dev>").strip()
    try:
        r = requests.post("https://api.resend.com/emails",
                          headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                          json={"from": sender, "to": [x.strip() for x in _recipient().split(",")],
                                "subject": subject, "html": html_body, "text": text_body}, timeout=30)
        if r.status_code in (200, 201):
            log.info("Email sent via Resend."); return True
        log.error("Resend FAILED: HTTP %s — %s", r.status_code, r.text[:300])
    except Exception as exc:
        log.error("Resend FAILED: %s", exc)
    return False


def send_newsletter(subject, html_body, text_body) -> bool:
    tried = []
    if os.getenv("GMAIL_ADDRESS") and os.getenv("GMAIL_APP_PASSWORD"):
        tried.append("Gmail")
        if _send_gmail(subject, html_body, text_body):
            return True
    if os.getenv("RESEND_API_KEY"):
        tried.append("Resend")
        if _send_resend(subject, html_body, text_body):
            return True
    log.error("Email NOT sent: %s", "all backends failed (%s)" % ", ".join(tried) if tried
              else "set GMAIL_ADDRESS + GMAIL_APP_PASSWORD")
    return False


# ===========================================================================
# Orchestrate
# ===========================================================================
def _load() -> Dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, ValueError):
        return {}


def _save(state) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def select(state) -> List[Dict]:
    sent = state.setdefault("sent", {})
    picks = []
    for a in AUTHORS:
        seen = set(sent.get(a["key"], []))
        nxt = next((e for e in a["essays"] if e["url"] not in seen), None)
        if nxt is None:
            log.info("%s fully read — recycling from the top.", a["name"])
            sent[a["key"]] = []; nxt = a["essays"][0]
        sent.setdefault(a["key"], []).append(nxt["url"])
        log.info("%s: %s", a["name"], nxt["title"])
        picks.append({"author": a, "entry": nxt})
    return picks


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
                 "SET" if os.getenv("RESEND_API_KEY") else "off", _recipient())
        if not args.force and state.get("last_sent_date") == today:
            log.info("Already sent today (%s) — nothing to do.", today)
            return 0

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY")) if os.getenv("ANTHROPIC_API_KEY") else None
    if client is None:
        log.warning("ANTHROPIC_API_KEY not set — takeaways will be placeholders.")

    picks = select(state)
    issue = [{"author": p["author"]["name"], "title": p["entry"]["title"], "url": p["entry"]["url"],
              **summarize(p["author"]["name"], p["entry"]["title"],
                          fetch_text(p["author"], p["entry"]["url"]), client)} for p in picks]
    date_str = datetime.now().strftime("%A, %B %d, %Y")
    html_body, text_body = render_html(issue, date_str), render_text(issue, date_str)
    subject = f"📚 The VC Reading Room — {datetime.now().strftime('%b %d')}"

    if args.dry_run:
        out = STATE_FILE.parent / "preview.html"
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(html_body)
        print("\n" + text_body); log.info("Dry run complete. Preview at %s", out)
        return 0

    if not send_newsletter(subject, html_body, text_body):
        log.error("Email FAILED — not advancing rotation; the next run will retry.")
        return 1
    state["last_sent_date"] = today
    _save(state)
    log.info("Done — emailed %d essays.", len(issue))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
