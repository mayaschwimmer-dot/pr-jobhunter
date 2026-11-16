"""אייס (ice.co.il/jobs) - מדור דרושים של עולם התקשורת, הפרסום והשיווק. פענוח HTML."""
from __future__ import annotations

import re
from typing import List

from bs4 import BeautifulSoup

from .. import config
from ..models import Job
from .util import http_get, polite_sleep, parse_date, pr_relevant, too_old

BASE = "https://www.ice.co.il"
PAGES = ["/jobs", "/jobs?page=2"]


def _t(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""


def parse(html: str) -> List[Job]:
    soup = BeautifulSoup(html, "lxml")
    out: List[Job] = []
    for rec in soup.select("div.JobRecord"):
        a = rec.select_one("a.jobName[href]")
        if a is None:
            continue
        m = re.search(r"/jobs/ById/(\d+)", a["href"])
        if not m:
            continue
        title = _t(a)
        rows = [_t(r) for r in rec.select(".body-row")]
        company = rows[0] if rows else ""
        location = rows[1] if len(rows) > 1 else ""
        desc = _t(rec.select_one(".positionDescription"))
        if not pr_relevant(title, desc[:300]):
            continue
        date_txt = _t(rec.select_one("span.date"))
        posted = parse_date(date_txt)
        if too_old(posted, config.BOARD_MAX_AGE_DAYS):
            continue
        out.append(Job(
            id="ice:" + m.group(1), source="אייס", title=title,
            company="" if company == "חסוי" else company, location=location,
            url="%s/jobs/ById/%s" % (BASE, m.group(1)), posted_at=posted,
            posted_text=date_txt, description=desc,
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
