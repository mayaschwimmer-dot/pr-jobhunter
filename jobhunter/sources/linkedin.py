"""לינקדאין - ה-API האורחי הציבורי (ללא התחברות, ללא חשבון)."""
from __future__ import annotations

import re
import time
from datetime import datetime
from typing import List
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .. import config
from ..models import Job
from .util import http_get, polite_sleep, extract_phones, extract_emails

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/%s"


def _txt(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""


def parse_cards(html: str) -> List[Job]:
    soup = BeautifulSoup(html, "lxml")
    jobs: List[Job] = []
    for card in soup.select("div.base-card"):
        urn = card.get("data-entity-urn", "")
        m = re.search(r"(\d+)$", urn)
        if not m:
            continue
        jid = m.group(1)
        title = _txt(card.select_one(".base-search-card__title"))
        if not title:
            continue
        company = _txt(card.select_one(".base-search-card__subtitle"))
        location = _txt(card.select_one(".job-search-card__location"))
        t = card.select_one("time")
        posted_at = None
        posted_text = ""
        if t is not None:
            posted_text = _txt(t)
            try:
                posted_at = datetime.fromisoformat(t.get("datetime", ""))
            except ValueError:
                posted_at = None
        jobs.append(Job(
            id="li:" + jid, source="LinkedIn", title=title, company=company,
            location=location, url="https://www.linkedin.com/jobs/view/" + jid,
            posted_at=posted_at, posted_text=posted_text,
        ))
    return jobs


def fetch() -> List[Job]:
    found = {}
    errors = []
    for i, q in enumerate(config.LINKEDIN_QUERIES):
        if i:
            polite_sleep()
        params = {
            "keywords": q, "location": "Israel", "geoId": "101620260",
            "f_TPR": config.LINKEDIN_TIME_FILTER, "sortBy": "DD", "start": 0,
        }
        try:
            r = http_get(SEARCH_URL, params=params)
        except Exception as e:  # noqa: BLE001 - שגיאת רשת בשאילתה אחת לא מפילה את השאר
            errors.append("%s: %s" % (q, e))
            continue
        if r.status_code == 429:
            time.sleep(8)           # ניסיון חוזר אחד אחרי המתנה
            try:
                r = http_get(SEARCH_URL, params=params)
            except Exception as e:  # noqa: BLE001
                errors.append("%s: %s" % (q, e))
                break
        if r.status_code == 429:
            errors.append("429 (הגבלת קצב) - עוצר")
            break
        if r.status_code != 200:
            errors.append("%s: HTTP %d" % (q, r.status_code))
            continue
        for job in parse_cards(r.text):
            found.setdefault(job.id, job)
    if not found and errors:
        raise RuntimeError("; ".join(errors[:3]))
    if errors:
        print("  [LinkedIn] אזהרות: " + "; ".join(errors[:3]))
    return list(found.values())


def enrich(job: Job) -> bool:
    """מביא תיאור + שם המגייס (אם מופיע) לעמוד משרה אחד. מחזיר True בהצלחה."""
    jid = job.id.split(":", 1)[1]
    r = http_get(DETAIL_URL % jid)
    if r.status_code != 200:
        return False
    soup = BeautifulSoup(r.text, "lxml")
    desc_el = soup.select_one("div.show-more-less-html__markup") or \
        soup.select_one("div.description__text")
    desc = desc_el.get_text("\n", strip=True) if desc_el else ""
    crit = [_txt(e) for e in soup.select(".description__job-criteria-text")]
    if crit:
        # רמת בכירות/סוג משרה משמשים לניקוד
        desc = desc + "\n" + " | ".join(crit)
    job.description = desc
    # צוות הגיוס / מפרסם המשרה - רק אם מופיע בעמוד הציבורי
    for a in soup.select("a[href*='linkedin.com/in/']"):
        name = _txt(a)
        if name and len(name) < 80:
            job.recruiter_name = name
            p = urlparse(a["href"])
            job.recruiter_url = "%s://%s%s" % (p.scheme, p.netloc, p.path)
            break
    job.phones = extract_phones(desc)
    job.emails = extract_emails(desc)
    return True
