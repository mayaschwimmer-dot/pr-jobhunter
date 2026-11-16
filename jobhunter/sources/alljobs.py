"""אולג'ובס (alljobs.co.il) - חיפוש אורחי ציבורי, פענוח HTML."""
from __future__ import annotations

import re
from typing import List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from .. import config
from ..models import Job
from .util import http_get, polite_sleep, parse_relative

BASE = "https://www.alljobs.co.il"
SEARCH = BASE + "/SearchResultsGuest.aspx?page=1&position=&type=&freetxt=%s&city=&region="


def _t(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""


def parse(html: str) -> List[Job]:
    soup = BeautifulSoup(html, "lxml")
    out: List[Job] = []
    for card in soup.select("div.job-content-top"):
        a = card.select_one(".job-content-top-title a[href*='JobID=']")
        if a is None:
            continue
        m = re.search(r"JobID=(\d+)", a["href"])
        if not m:
            continue
        jid = m.group(1)
        title = _t(a.select_one("h2")) or a.get("title", "").replace("דרושים |", "").strip()
        comp_a = card.select_one(".job-content-top-title .T14 a")
        loc_el = card.select_one(".job-content-top-location")
        loc = _t(loc_el).replace("מיקום המשרה:", "").strip()
        date_txt = _t(card.select_one(".job-content-top-date"))
        desc = _t(card.select_one(".job-content-top-desc"))
        typ = _t(card.select_one(".job-content-top-type")).replace("סוג משרה:", "").strip()
        out.append(Job(
            id="aj:" + jid, source="אולג'ובס", title=title, company=_t(comp_a),
            location=loc, url="%s/Search/UploadSingle.aspx?JobID=%s" % (BASE, jid),
            posted_at=parse_relative(date_txt), posted_text=date_txt,
            description=desc + (" . היקף: " + typ if typ else ""),
        ))
    return out


def fetch() -> List[Job]:
    found = {}
    errors = []
    n = 0
    for i, q in enumerate(config.BOARD_QUERIES):
        # עמוד 2 רק לשאילתות המרכזיות (שלוש הראשונות), כדי לא להאריך את ההרצה
        for page in range(1, (config.EXTRA_PAGES if i < 3 else 1) + 1):
            if n:
                polite_sleep(-config.REQUEST_DELAY + 0.7)
            n += 1
            try:
                r = http_get((SEARCH % quote_plus(q)).replace("page=1", "page=%d" % page, 1))
                if r.status_code != 200:
                    errors.append("%s: HTTP %d" % (q, r.status_code))
                    break
                got = parse(r.text)
                for j in got:
                    found.setdefault(j.id, j)
                if not got:
                    break
            except Exception as e:  # noqa: BLE001
                errors.append("%s: %s" % (q, e))
                break
    if not found and errors:
        raise RuntimeError("; ".join(errors[:3]))
    return list(found.values())
