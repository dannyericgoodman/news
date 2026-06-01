"""Best-effort fetch of an essay's full text, for summarizing.

If a site blocks us, returns None and the summarizer falls back to the model's
own knowledge of the canonical essay.
"""

import logging
import re
from typing import Dict, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"),
    "Accept": "text/html,application/json,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
MAX_CHARS = 16000


def _get(url, **kw):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30, **kw)
        if r.status_code == 200:
            return r
        logger.warning("GET %s -> HTTP %s", url, r.status_code)
    except requests.RequestException as exc:
        logger.warning("GET %s failed: %s", url, exc)
    return None


def _clean(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()[:MAX_CHARS]


def fetch_text(author: Dict, url: str) -> Optional[str]:
    try:
        if author.get("kind") == "wp" and author.get("api_url"):
            slug = urlparse(url).path.strip("/").split("/")[-1]
            r = _get(author["api_url"], params={"slug": slug, "_fields": "content"})
            if r:
                try:
                    data = r.json()
                    if isinstance(data, list) and data:
                        html = (data[0].get("content") or {}).get("rendered", "")
                        txt = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
                        if txt:
                            return _clean(txt)
                except ValueError:
                    pass
        r = _get(url)
        if not r:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        root = soup.find("article") or soup.body or soup
        return _clean(root.get_text("\n", strip=True))
    except Exception as exc:
        logger.error("Fetch failed for %s: %s", url, exc)
        return None
