"""כלי עזר משותפים למקורות: HTTP מנומס, פענוח זמנים יחסיים, חילוץ טלפונים/מיילים."""
from __future__ import annotations

import re
import time
from datetime import datetime, timedelta
from typing import List, Optional

import requests

from .. import config

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_session = requests.Session()
_session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})


def http_get(url: str, params=None, headers=None) -> requests.Response:
    """GET עם timeout. לא זורק על קודי סטטוס - הקורא בודק status_code."""
    resp = _session.get(url, params=params, headers=headers,
                        timeout=config.REQUEST_TIMEOUT)
    if resp.encoding is None or resp.encoding.lower() in ("iso-8859-1", "ascii"):
        resp.encoding = resp.apparent_encoding or "utf-8"
    return resp


def polite_sleep(extra: float = 0.0) -> None:
    time.sleep(config.REQUEST_DELAY + extra)


_BIDI = re.compile(r"[‎‏‪-‮⁦-⁩]")


def parse_relative(text: str, now: Optional[datetime] = None) -> Optional[datetime]:
    """'לפני 4 שעות' / '1 ימים' / 'היום' / 'אתמול' -> datetime משוער."""
    if not text:
        return None
    now = now or datetime.now()
    t = _BIDI.sub("", text)
    m = re.search(r"\d+", t)
    n = int(m.group()) if m else 1
    if "היום" in t:
        return now
    if "אתמול" in t:
        return now - timedelta(days=1)
    if "דקות" in t or "דקה" in t:
        return now - timedelta(minutes=n)
    if "שעתיים" in t:
        return now - timedelta(hours=2)
    if "שעות" in t or "שעה" in t:
        return now - timedelta(hours=n)
    if "יומיים" in t:
        return now - timedelta(days=2)
    if "ימים" in t or "יום" in t:
        return now - timedelta(days=n)
    if "שבועיים" in t:
        return now - timedelta(days=14)
    if "שבוע" in t:
        return now - timedelta(days=7 * n)
    if "חודש" in t:
        return now - timedelta(days=30 * n)
    return None


_PHONE_RE = re.compile(
    r"(?<![\d-])(?:\+972[-\s]?|972[-\s]?|0)(?:5\d|[23489]|7\d)[-\s]?\d{3}[-\s]?\d{4}(?!\d)"
)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def extract_phones(text: str) -> List[str]:
    out: List[str] = []
    for m in _PHONE_RE.finditer(text or ""):
        p = re.sub(r"[\s]", "", m.group())
        if p not in out:
            out.append(p)
    return out


def extract_emails(text: str) -> List[str]:
    out: List[str] = []
    for m in _EMAIL_RE.finditer(text or ""):
        e = m.group().rstrip(".")
        if e.lower() not in [x.lower() for x in out]:
            out.append(e)
    return out
