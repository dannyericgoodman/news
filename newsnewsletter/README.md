# 📚 Daily VC Reading Newsletter

A single email every morning with one **archived, never-repeated** essay each
from Paul Graham, Bill Gurley, and Andrew Chen — each with **Claude-written key
takeaways + an "investor angle"** for an aspiring elite venture investor. Runs
on GitHub Actions; no server.

- **Never repeats:** each author's essays are sent in order, tracked in
  `newsletter/data/state.json`, until the list is exhausted, then it recycles.
- **Add/remove authors** by editing `newsletter/authors.py` (see the comment at top).
- **Delivery:** Gmail SMTP (proven, no domain needed); Resend optional.
- **Sends at most once/day** even if the workflow fires multiple times.

## Setup (~5 minutes)

### 1. Add the files to this repo
Commit everything in this bundle to the repo root (`newsletter/`, `.github/`,
`requirements.txt`, `README.md`).

### 2. Add secrets — Settings → Secrets and variables → Actions → New repository secret
| Secret | Required? | Value |
|--------|-----------|-------|
| `GMAIL_ADDRESS` | ✅ | the Gmail that sends (e.g. `danny.eric.goodman@gmail.com`) |
| `GMAIL_APP_PASSWORD` | ✅ | a 16-char Google **App Password** (Google account → 2-Step Verification → App passwords). Spaces are auto-stripped. |
| `ANTHROPIC_API_KEY` | ✅ | for the Claude takeaways |
| `NEWSLETTER_TO` | optional | recipient; defaults to `danny.eric.goodman@gmail.com` |

> These are the same keys you used before. GitHub never lets anyone read a
> secret's value back, so they have to be re-entered here (not copyable between
> repos).

### 3. Done
- **Automatic:** fires ~7:05/7:35/8:05am Central daily; sends once.
- **Test now:** Actions → **Daily Newsletter** → **Run workflow** (forces a send).

## How it verifies itself
Each run commits `newsletter/data/last_run.log` (and the rotation state). If an
email ever fails, the run goes **red** (GitHub emails you) and the log shows the
exact reason; rotation does **not** advance, so nothing is skipped.

## Local use
```bash
pip install -r requirements.txt
python -m newsletter.main --dry-run   # writes newsletter/data/preview.html, no send
```

## Add or remove an author
Edit `newsletter/authors.py`: append/delete a dict with `key`, `name`, `kind`
("pg" static HTML, or "wp" WordPress + `api_url`), and an ordered `essays` list
of `{title, url}`. That's it — rotation adapts automatically.
