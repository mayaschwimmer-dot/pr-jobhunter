"""תעשיה (taasiya.co.il) - לוח דרושים לתקשורת, פרסום, תוכן, הפקה ויח"צ. פענוח HTML."""
from __future__ import annotations

import re
from typing import List

from bs4 import BeautifulSoup

from .. import config
from ..models import Job
from .util import http_get, polite_sleep, parse_date, pr_relevant, too_old

BASE = "https://www.taasiya.co.il"
# (כתובת, האם כל התוצאות רלוונטיות מראש - קטגוריית יח"צ)
LISTINGS = [
    (BASE + "/jobs/?category=102&sub_category=105", True),    # יחסי ציבור
    (BASE + "/jobs/", False),                                  # כל המשרות החדשות
    (BASE + "/jobs/?start=0&my_jobs=0&limit=20&category=102", False),  # שיווק/ניהול/אדמיניסטרציה
]
MAX_DETAIL = 10


def _t(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""


def parse(html: str, trusted: bool) -> List[Job]:
    soup = BeautifulSoup(html, "lxml")
    out: List[Job] = []
    for it in soup.select("div.resultItem"):
        a = it.select_one("[itemprop=title] a[href]")
        if a is None:
            continue
        m = re.search(r"/jobs/views/(\d+)\.htm", a["href"])
        if not m:
            continue
        title = _t(a)
        if not trusted and not pr_relevant(title):
            continue
        date_txt = _t(it.select_one("[itemprop=datePosted]"))
        posted = parse_date(date_txt)
        if too_old(posted, config.BOARD_MAX_AGE_DAYS):
            continue
        out.append(Job(
            id="ta:" + m.group(1), source="תעשיה", title=title,
            location=_t(it.select_one("[itemprop=jobLocation]")),
            url="%s/jobs/views/%s.htm" % (BASE, m.group(1)),
            posted_at=posted, posted_text=date_txt,
            description=". היקף: " + _t(it.select_one("[itemprop=employmentType]")),
        ))
    return out


def fetch() -> List[Job]:
    found = {}
    errors = []
    for i, (url, trusted) in enumerate(LISTINGS):
        if i:
            polite_sleep(-config.REQUEST_DELAY + 0.5)
        try:
            r = http_get(url)
            if r.status_code != 200:
                errors.append("HTTP %d" % r.status_code)
                continue
            for j in parse(r.text, trusted):
                found.setdefault(j.id, j)
        except Exception as e:  # noqa: BLE001
            errors.append(str(e))
    if not found and errors:
        raise RuntimeError("; ".join(errors[:3]))
    # תיאור מלא מעמוד המשרה (מוגבל, כדי לא להאריך את ההרצה)
    for j in list(found.values())[:MAX_DETAIL]:
        try:
            polite_sleep(-config.REQUEST_DELAY + 0.4)
            r = http_get(j.url)
            if r.status_code == 200:
                d = BeautifulSoup(r.text, "lxml").select_one("[itemprop=description]")
                if d is not None:
                    j.description = _t(d) + " " + j.description
        except Exception:  # noqa: BLE001
            pass
    return list(found.values())
