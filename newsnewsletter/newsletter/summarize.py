"""Claude-written takeaways for an essay, tailored for an aspiring elite VC.

If the full text was fetched, summarize it; otherwise summarize the canonical
essay from the model's knowledge (guarded so it won't fabricate). Tries Opus 4.8
then Sonnet so one bad model id can't blank everything.
"""

import json
import logging
import os
import re
from typing import Dict, List, Optional

from anthropic import Anthropic

logger = logging.getLogger(__name__)


def _models() -> List[str]:
    chain = ([os.getenv("VC_MODEL")] if os.getenv("VC_MODEL") else []) + \
            ["claude-opus-4-8", "claude-sonnet-4-20250514"]
    out, seen = [], set()
    for m in chain:
        if m and m not in seen:
            seen.add(m); out.append(m)
    return out


_SHAPE = """Respond with ONLY a JSON object in exactly this shape:
{{
  "one_liner": "<one sentence: the single core idea>",
  "takeaways": ["<3-5 crisp, specific, one-sentence takeaways; durable mental \
models and investor judgment, not surface summary>"],
  "investor_angle": "<one sentence on why this matters for an early-stage VC's \
decisions or founder evaluation>"
}}"""

PROMPT_TEXT = ("You are a mentor helping an aspiring elite early-stage venture capitalist "
               "study the canon. Distill this essay by {author}, \"{title}\", for a busy "
               "investor. " + _SHAPE + "\n\nESSAY:\n---\n{text}\n---")

PROMPT_KNOWLEDGE = ("You are a mentor helping an aspiring elite early-stage venture "
                    "capitalist study the canon. Summarize the well-known essay \"{title}\" "
                    "by {author} from your own knowledge. If you are not confident you know "
                    "this specific essay, return {{\"one_liner\":\"\",\"takeaways\":[],"
                    "\"investor_angle\":\"\"}} and nothing else — do NOT fabricate. " + _SHAPE)


def _fallback(title: str, reason: str) -> Dict:
    return {"one_liner": f"Classic essay: {title}.",
            "takeaways": [f"Auto-summary unavailable ({reason}) — read it via the link below."],
            "investor_angle": "Part of the early-stage VC canon worth reading in full.",
            "ok": False}


def _parse(raw: str) -> Dict:
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    data = json.loads(m.group(0) if m else raw)
    tk = data.get("takeaways") or []
    if isinstance(tk, str):
        tk = [tk]
    return {"one_liner": str(data.get("one_liner", "")).strip(),
            "takeaways": [str(t).strip() for t in tk if str(t).strip()],
            "investor_angle": str(data.get("investor_angle", "")).strip(), "ok": True}


def summarize(author_name, title, text, url, client: Optional[Anthropic] = None) -> Dict:
    if not os.getenv("ANTHROPIC_API_KEY") and client is None:
        return _fallback(title, "ANTHROPIC_API_KEY not set")
    if text:
        prompt, mode = PROMPT_TEXT.format(author=author_name, title=title, text=text), "full-text"
    else:
        logger.warning("No fetched text for '%s' — summarizing from knowledge.", title)
        prompt, mode = PROMPT_KNOWLEDGE.format(author=author_name, title=title), "knowledge"
    client = client or Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    last = None
    for model in _models():
        try:
            resp = client.messages.create(model=model, max_tokens=1024,
                                           messages=[{"role": "user", "content": prompt}])
            res = _parse(resp.content[0].text)
            if res["takeaways"]:
                logger.info("Summarized '%s' (%s, %s).", title, mode, model)
                return res
            last = "empty (essay not recognized)"
        except Exception as exc:
            last = str(exc); logger.warning("Model %s failed for '%s': %s", model, title, exc)
    logger.error("Summary failed for '%s': %s", title, last)
    return _fallback(title, "fetch blocked & not recognized" if mode == "knowledge" else "model error")
