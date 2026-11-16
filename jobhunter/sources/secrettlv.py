"""Secret Tel Aviv Jobs (jobs.secrettelaviv.com) - לוח משרות (WP Job Board). פענוח HTML."""
from __future__ import annotations

import re
from datetime import datetime
from typing import List

from bs4 import BeautifulSoup

from .. import config
from ..models import Job
from .util import http_get, polite_sleep, pr_relevant, too_old

BASE = "https://jobs.secrettelaviv.com"
PAGES = ["/", "/page/2/", "/page/3/"]
_MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def _t(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""


def _date(text: str):
    m = re.search(r"([A-Za-z]{3})[a-z]*,?\s+(\d{1,2})", text)
    if not m or m.group(1).lower() not in _MONTHS:
        return None
    now = datetime.now()
    try:
        d = datetime(now.year, _MONTHS[m.group(1).lower()], int(m.group(2)))
    except ValueError:
        return None
    return d if d <= now else d.replace(year=now.year - 1)


def parse(html: str) -> List[Job]:
    soup = BeautifulSoup(html, "lxml")
    out: List[Job] = []
    for row in soup.select("div.wpjb-grid-row.wpjb-click-area"):
        a = row.select_one(".wpjb-col-title a[href]")
        if a is None:
            continue
        title = _t(a)
        cats = " ".join(c.replace("wpjb-category-", "").replace("-", " ")
                        for c in row.get("class", []) if c.startswith("wpjb-category-"))
        if not pr_relevant(title):
            continue
        date_txt = _t(row.select_one(".wpjb-col-15 .wpjb-line-major"))
        posted = _date(date_txt)
        if too_old(posted, config.BOARD_MAX_AGE_DAYS):
            continue
        slug = a["href"].rstrip("/").rsplit("/", 1)[-1]
        out.append(Job(
            id="stlv:" + slug, source="Secret TLV", title=title,
            company=_t(row.select_one(".wpjb-col-title .wpjb-sub")),
            location=_t(row.select_one(".wpjb-col-location .wpjb-glyphs")),
            url=a["href"], posted_at=posted, posted_text=date_txt,
            description="קטגוריות: " + cats,
        ))
    return out


def fetch() -> List[Job]:
    found = {}
    errors = []
    for i, path in enumerate(PAGES):
        if i:
            polite_sleep(-config.REQUEST_DELAY + 0.5)
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
