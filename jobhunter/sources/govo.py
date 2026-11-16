"""GOVO (govojobs.co.il) - מכרזי כוח אדם ברשויות מקומיות (רשימה ציבורית; אזור/תחום למנויים בלבד).

מחליף את gov.il (חסום). משרות דוברות ויח"צ ברשויות מופיעות כאן. סינון מקדים לפי כותרת.
"""
from __future__ import annotations

import re
from typing import List

from bs4 import BeautifulSoup

from .. import config
from ..models import Job
from .util import http_get, polite_sleep, pr_relevant

BASE = "https://www.govojobs.co.il"
LIST = BASE + ("/govjobs/more/%D7%9E%D7%9B%D7%A8%D7%96%D7%99-%D7%9B%D7%95%D7%97-%D7%90%D7%93%D7%9D-"
               "%D7%91%D7%A8%D7%A9%D7%95%D7%99%D7%95%D7%AA-%D7%94%D7%9E%D7%A7%D7%95%D7%9E%D7%99%D7%95%D7%AA"
               "?page={page}")
MAX_PAGES = 3


def _t(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""


def parse(html: str) -> List[Job]:
    soup = BeautifulSoup(html, "lxml")
    out: List[Job] = []
    for it in soup.select("div.tbl_item_v2"):
        a = it.select_one("h2.title a[href]")
        if a is None:
            continue
        m = re.search(r"/job/([0-9a-f-]{36})", a["href"])
        if not m:
            continue
        title = re.sub(r"^משרת:\s*", "", _t(a)).strip(" ,")
        if not pr_relevant(title):
            continue
        out.append(Job(
            id="govo:" + m.group(1), source="מכרזי רשויות", title=title,
            company="רשות מקומית (מכרז)", url=BASE + a["href"],
            posted_text=_t(it.select_one(".time p")),
            description=_t(it),
        ))
    return out


def fetch() -> List[Job]:
    found = {}
    errors = []
    for p in range(1, MAX_PAGES + 1):
        if p > 1:
            polite_sleep(-config.REQUEST_DELAY + 0.4)
        try:
            r = http_get(LIST.replace("{page}", str(p)))
            if r.status_code != 200:
                errors.append("HTTP %d" % r.status_code)
                break
            for j in parse(r.text):
                found.setdefault(j.id, j)
        except Exception as e:  # noqa: BLE001
            errors.append(str(e))
            break
    if not found and errors:
        raise RuntimeError("; ".join(errors[:3]))
    return list(found.values())

