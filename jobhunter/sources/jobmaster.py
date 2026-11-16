"""ג'ובמאסטר (jobmaster.co.il) - חיפוש ציבורי, פענוח HTML."""
from __future__ import annotations

import re
from typing import List
from urllib.parse import quote

from bs4 import BeautifulSoup

from .. import config
from ..models import Job
from .util import http_get, polite_sleep, parse_relative

BASE = "https://www.jobmaster.co.il"


def _t(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""


def parse(html: str) -> List[Job]:
    soup = BeautifulSoup(html, "lxml")
    out: List[Job] = []
    for art in soup.select("article.JobItem"):
        a = art.select_one("a.CardHeader")
        if a is None:
            continue
        m = re.search(r"key=(\d+)", a.get("href", ""))
        if not m:
            continue
        jid = m.group(1)
        date_txt = _t(art.select_one("span.Gray")).replace("פורסם", "").strip()
        locs = ", ".join(_t(x) for x in art.select("li.jobLocation a"))
        types = ", ".join(_t(x) for x in art.select("li.jobType a"))
        out.append(Job(
            id="jm:" + jid, source="ג'ובמאסטר", title=_t(a),
            company=_t(art.select_one("a.CompanyNameLink")), location=locs,
            url="%s/jobs/checknum.asp?key=%s" % (BASE, jid),
            posted_at=parse_relative(date_txt), posted_text=date_txt,
            description=_t(art.select_one(".jobShortDescription"))
            + (" . היקף: " + types if types else ""),
        ))
    return out


def fetch() -> List[Job]:
    found = {}
    errors = []
    for i, q in enumerate(config.BOARD_QUERIES):
        if i:
            polite_sleep()
        try:
            r = http_get(BASE + "/jobs/", params={"q": q})
            if r.status_code != 200:
                errors.append("%s: HTTP %d" % (q, r.status_code))
                continue
            for j in parse(r.text):
                found.setdefault(j.id, j)
        except Exception as e:  # noqa: BLE001
            errors.append("%s: %s" % (q, e))
    if not found and errors:
        raise RuntimeError("; ".join(errors[:3]))
    return list(found.values())
