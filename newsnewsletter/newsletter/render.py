"""Render the daily issue as an HTML email body (+ plain-text fallback).

An issue is a list of {author, title, url, one_liner, takeaways[list], investor_angle}.
"""

import html
from typing import Dict, List


def _esc(s: str) -> str:
    return html.escape(s or "")


def render_html(issues: List[Dict], date_str: str) -> str:
    cards = []
    for it in issues:
        takeaways = "".join(
            f"<li style='margin:0 0 6px;line-height:1.5;'>{_esc(t)}</li>" for t in it["takeaways"])
        angle = ""
        if it.get("investor_angle"):
            angle = (f"<p style='margin:14px 0 0;padding:10px 14px;background:#f4f6fb;"
                     f"border-left:3px solid #4a6cf7;border-radius:4px;font-size:14px;color:#33415c;'>"
                     f"<strong>Investor angle:&nbsp;</strong>{_esc(it['investor_angle'])}</p>")
        cards.append(f"""
        <tr><td style="padding:0 0 28px;">
          <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
                 style="border:1px solid #e6e8ec;border-radius:10px;overflow:hidden;">
            <tr><td style="background:#0f172a;padding:14px 20px;">
              <span style="color:#93a4c4;font-size:12px;letter-spacing:1px;text-transform:uppercase;">{_esc(it['author'])}</span>
            </td></tr>
            <tr><td style="padding:20px;">
              <a href="{_esc(it['url'])}" style="color:#0f172a;text-decoration:none;font-size:20px;font-weight:700;line-height:1.3;">{_esc(it['title'])}</a>
              <p style="margin:8px 0 16px;color:#52617a;font-style:italic;font-size:15px;line-height:1.5;">{_esc(it['one_liner'])}</p>
              <p style="margin:0 0 8px;font-size:13px;font-weight:700;color:#0f172a;text-transform:uppercase;letter-spacing:0.5px;">Key takeaways</p>
              <ul style="margin:0;padding-left:20px;color:#1f2937;font-size:15px;">{takeaways}</ul>
              {angle}
              <p style="margin:18px 0 0;">
                <a href="{_esc(it['url'])}" style="display:inline-block;background:#4a6cf7;color:#ffffff;text-decoration:none;padding:9px 18px;border-radius:6px;font-size:14px;font-weight:600;">Read the full essay →</a>
              </p>
            </td></tr>
          </table>
        </td></tr>""")
    return f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#eef1f6;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background:#eef1f6;padding:28px 12px;">
        <tr><td align="center"><table width="600" cellpadding="0" cellspacing="0" role="presentation" style="max-width:600px;width:100%;">
          <tr><td style="padding:0 0 22px;text-align:center;">
            <h1 style="margin:0;font-size:24px;color:#0f172a;">The VC Reading Room</h1>
            <p style="margin:6px 0 0;color:#6b7890;font-size:14px;">Daily wisdom from the greats · {_esc(date_str)}</p>
          </td></tr>
          {''.join(cards)}
          <tr><td style="padding:6px 0 0;text-align:center;color:#9aa6bd;font-size:12px;line-height:1.6;">
            One classic essay each from your chosen investors.<br>Study daily. Compound the wisdom.
          </td></tr>
        </table></td></tr>
      </table></body></html>"""


def render_text(issues: List[Dict], date_str: str) -> str:
    lines = [f"THE VC READING ROOM — {date_str}", "=" * 48, ""]
    for it in issues:
        lines += [f"## {it['author']}: {it['title']}", f"   {it['one_liner']}", "", "   KEY TAKEAWAYS:"]
        lines += [f"   - {t}" for t in it["takeaways"]]
        if it.get("investor_angle"):
            lines.append(f"   INVESTOR ANGLE: {it['investor_angle']}")
        lines += [f"   Read: {it['url']}", "", "-" * 48, ""]
    return "\n".join(lines)
