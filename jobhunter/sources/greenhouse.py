"""לוחות Greenhouse ציבוריים (JSON) של חברות ישראליות נבחרות - סינון מקדים לפי כותרת."""
from __future__ import annotations

from datetime import datetime
from typing import List

from .. import config
from ..models import Job
from ..scoring import norm, hits
from .util import http_get, polite_sleep

API = "https://boards-api.greenhouse.io/v1/boards/%s/jobs"


def _in_region(loc: str) -> bool:
    l = norm(loc)
    if not l:
        return True
    return bool(hits(["israel", "ישראל", "remote", "hybrid"] + config.TARGET_LOCATIONS, l))


def fetch() -> List[Job]:
    out: List[Job] = []
    errors = []
    for i, (slug, name) in enumerate(config.GREENHOUSE_BOARDS.items()):
        if i:
            polite_sleep(-config.REQUEST_DELAY + 0.4)
        try:
            r = http_get(API % slug)
            if r.status_code != 200:
                errors.append("%s: HTTP %d" % (slug, r.status_code))
                continue
            for j in r.json().get("jobs", []):
                title = j.get("title", "")
                loc = (j.get("location") or {}).get("name", "")
                if not hits(config.BOARD_TITLE_PREFILTER, norm(title)) or not _in_region(loc):
                    continue
                upd = None
                try:
                    upd = datetime.fromisoformat((j.get("updated_at") or "")[:19])
                except ValueError:
                    pass
                out.append(Job(
                    id="gh:%s:%s" % (slug, j.get("id")), source="Greenhouse",
                    title=title, company=name, location=loc,
                    url=j.get("absolute_url", ""), posted_at=upd,
                    posted_text="עודכן " + (upd.strftime("%d/%m") if upd else ""),
                ))
        except Exception as e:  # noqa: BLE001
            errors.append("%s: %s" % (slug, e))
    if not out and errors and len(errors) == len(config.GREENHOUSE_BOARDS):
        raise RuntimeError("; ".join(errors[:3]))
    return out
