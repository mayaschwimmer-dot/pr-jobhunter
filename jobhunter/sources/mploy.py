"""Mploy (mploy.co.il) - דפי תגיות/חיפוש של יחסי ציבור ודוברות. פענוח HTML."""
from __future__ import annotations

import re
from datetime import datetime
from typing import List

from bs4 import BeautifulSoup

from .. import config
from ..models import Job
from .util import http_get, polite_sleep, pr_relevant, parse_relative, too_old

BASE = "https://www.mploy.co.il"
PAGES = [
    "/job/tagged/%D7%99%D7%97%D7%A1%D7%99-%D7%A6%D7%99%D7%91%D7%95%D7%A8-%D7%95%D7%93%D7%95%D7%91%D7%A8%D7%95%D7%AA",
    "/job/search/%D7%99%D7%97%D7%A6",
    "/job/search/%D7%93%D7%95%D7%91%D7%A8%D7%95%D7%AA",
]


def _t(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""


def parse(html: str) -> List[Job]:
    soup = BeautifulSoup(html, "lxml")
    out: List[Job] = []
    for card in soup.select("div[data-jobid]"):
        jid = card["data-jobid"]
        a = card.select_one("a[href*='/job/details/']")
        if a is None:
            continue
        title = _t(a)
        tm = card.select_one("time")
        posted = None
        if tm is not None and tm.get("datetime"):
            try:
                posted = datetime.fromisoformat(tm["datetime"].replace("Z", "+00:00")) \
                    .astimezone().replace(tzinfo=None)
            except ValueError:
                posted = parse_relative(_t(tm))
        loc = _t(tm.find_next("p")) if tm is not None else ""
        desc = _t(card)
        if title in desc:
            desc = desc.split(title, 1)[1]
        if not pr_relevant(title, desc[:400]) or too_old(posted, config.BOARD_MAX_AGE_DAYS):
            continue
        out.append(Job(
            id="mp:" + jid, source="Mploy", title=title, location=loc,
            url=BASE + a["href"], posted_at=posted,
            posted_text=_t(tm) if tm is not None else "", description=desc,
        ))
    return out


def fetch() -> List[Job]:
    found = {}
    errors = []
    for i, path in enumerate(PAGES):
        if i:
            polite_sleep()
        try:
            r = http_get(BASE + path)
            if r.status_code != 200:
                errors.append("HTTP %d" % r.status_code)
                continue
            for j in parse(r.text):
                found.setdefault(j.id, j)
        except Exception as e:  # noqa: BLE001
            errors.append(str(e))
    if not found and errors:
        raise RuntimeError("; ".join(errors[:3]))
    return list(found.values())
