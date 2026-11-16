"""דרושים (drushim.co.il) - אתר Next.js; הנתונים ב-__NEXT_DATA__ כ-JSON."""
from __future__ import annotations

import json
from datetime import datetime
from typing import List
from urllib.parse import quote

from bs4 import BeautifulSoup

from .. import config
from ..models import Job
from .util import http_get, polite_sleep, parse_relative

BASE = "https://www.drushim.co.il"


def _jobs_from_html(html: str) -> list:
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return []
    data = json.loads(tag.string)
    queries = data["props"]["pageProps"]["dehydratedState"]["queries"]
    for q in queries:
        key = q.get("queryKey") or []
        if key and key[0] == "search-results":
            pages = (q["state"].get("data") or {}).get("pages") or []
            out = []
            for p in pages:
                out.extend(p.get("jobs") or [])
            return out
    return []


def fetch() -> List[Job]:
    found = {}
    errors = []
    for i, q in enumerate(config.BOARD_QUERIES):
        if i:
            polite_sleep()
        try:
            r = http_get("%s/jobs/search/%s/" % (BASE, quote(q)))
            if r.status_code != 200:
                errors.append("%s: HTTP %d" % (q, r.status_code))
                continue
            raw = _jobs_from_html(r.text)
        except Exception as e:  # noqa: BLE001
            errors.append("%s: %s" % (q, e))
            continue
        for j in raw:
            jid = str(j.get("id"))
            if not jid or "dr:" + jid in found:
                continue
            posted = None
            try:
                posted = datetime.fromisoformat(j.get("publishedAtIso") or "")
            except ValueError:
                posted = parse_relative(j.get("publishedAt", ""))
            cities = j.get("cities") or [j.get("city") or ""]
            found["dr:" + jid] = Job(
                id="dr:" + jid, source="דרושים", title=j.get("title", "").strip(),
                company=(j.get("companyName") or "").replace("- חסוי -", "חברה חסויה").strip(),
                location=", ".join(c for c in cities if c),
                url=BASE + (j.get("jobUrl") or "/job/" + jid + "/"),
                posted_at=posted, posted_text=j.get("publishedAt", ""),
                description=(j.get("description") or "") + " . ניסיון נדרש: "
                + (j.get("experience") or "") + " . היקף: " + (j.get("scope") or ""),
            )
    if not found and errors:
        raise RuntimeError("; ".join(errors[:3]))
    return list(found.values())
