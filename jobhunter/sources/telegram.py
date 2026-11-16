"""ערוצי טלגרם ציבוריים (תצוגת web ללא התחברות: https://t.me/s/<ערוץ>).

כל פוסט הוא משרה: כותרת = השורה הראשונה, תיאור = כל הטקסט.
רק פוסטים שעוברים סינון מקדים של יחצ/תקשורת נכנסים לניקוד.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import List

from bs4 import BeautifulSoup

from .. import config
from ..models import Job
from .util import http_get, polite_sleep, pr_relevant, too_old

_LEAD = re.compile(r"^[\W_]+", re.UNICODE)


def _title(text: str) -> str:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    # מדלגים על שורות הערה כמו "*אין לי שום קשר למשרה*"
    first = next((l for l in lines if "אין לי שום קשר" not in l), lines[0] if lines else "")
    first = _LEAD.sub("", first).strip("* ")
    if len(first) > 110:
        cut = re.split(r"(?<=[.!?:])\s", first, maxsplit=1)[0]
        first = cut if 20 <= len(cut) <= 110 else first[:107].rstrip() + "..."
    return first


def parse(html: str, channel: str, name: str) -> List[Job]:
    soup = BeautifulSoup(html, "lxml")
    out: List[Job] = []
    for m in soup.select("div.tgme_widget_message[data-post]"):
        box = m.select_one(".tgme_widget_message_text")
        if box is None:
            continue
        for br in box.find_all("br"):
            br.replace_with("\n")
        text = box.get_text("", strip=False).strip()
        post = m["data-post"]                       # channel/123
        pid = post.rsplit("/", 1)[-1]
        t = m.select_one("time[datetime]")
        posted = None
        if t is not None:
            try:
                posted = datetime.fromisoformat(t["datetime"]).astimezone().replace(tzinfo=None)
            except ValueError:
                posted = None
        if too_old(posted, config.TELEGRAM_MAX_AGE_DAYS):
            continue
        title = _title(text)
        if not title or not pr_relevant(text):
            continue
        out.append(Job(
            id="tg:%s:%s" % (channel, pid), source="טלגרם", title=title, company=name,
            url="https://t.me/%s/%s" % (channel, pid), posted_at=posted,
            posted_text=posted.strftime("%d/%m %H:%M") if posted else "",
            description=text,
        ))
    return out


def fetch() -> List[Job]:
    out: List[Job] = []
    errors = []
    for i, (ch, name) in enumerate(config.TELEGRAM_CHANNELS.items()):
        if i:
            polite_sleep(-config.REQUEST_DELAY + 0.5)
        try:
            r = http_get("https://t.me/s/" + ch)
            if r.status_code != 200:
                errors.append("%s: HTTP %d" % (ch, r.status_code))
                continue
            out.extend(parse(r.text, ch, name))
        except Exception as e:  # noqa: BLE001
            errors.append("%s: %s" % (ch, e))
    if not out and errors and len(errors) == len(config.TELEGRAM_CHANNELS):
        raise RuntimeError("; ".join(errors[:3]))
    return out
