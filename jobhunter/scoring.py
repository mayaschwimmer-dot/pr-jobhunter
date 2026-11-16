"""ניקוד משרות לפי מילות מפתח וכללים בלבד (ללא LLM). מחזיר ציון 0..100 וסיבות בעברית."""
from __future__ import annotations

import re
from functools import lru_cache
from typing import List, Tuple

from . import config
from .models import Job

_INVISIBLE = re.compile(r"[‎‏‪-‮⁦-⁩]")
_GENDER = re.compile(r"\s*[/(]\s*(?:ית|ים|ות|ת|ה)\s*\)?(?![א-ת])")
_HEB = re.compile(r"[א-ת]")
_LANGS = ("עברית|רוסית|ערבית|אנגלית|צרפתית|ספרדית|אמהרית|גרמנית|איטלקית|פורטוגזית"
          "|תורכית|טורקית|רומנית|שפות|שפה|סינית|הולנדית|פולנית|אוקראינית|גאורגית")
_SPEAKER_LANG = re.compile(r"דובר(?:ת|ים|ות|י)?\s+(?:את\s+)?(?:ה|ו|ב)?(?:" + _LANGS + ")")


def norm(text: str) -> str:
    """נרמול: אותיות קטנות, בלי גרשיים ובלי סיומות מגדר (דובר/ת -> דובר)."""
    t = (text or "").lower()
    t = _INVISIBLE.sub("", t)
    t = _GENDER.sub("", t)
    for ch in ('"', "״", "'", "’", "׳", "`", "”", "“"):
        t = t.replace(ch, "")
    t = _SPEAKER_LANG.sub(" ", t)   # "דובר רוסית" = דובר שפה, לא דוברות
    return re.sub(r"\s+", " ", t).strip()


@lru_cache(maxsize=None)
def _pattern(term: str) -> "re.Pattern[str]":
    t = norm(term)
    if _HEB.search(t):
        # עברית: תחילת מילה, עם אפשרות לתחילית אחת-שתיים (ו/ה/ב/ל/כ/ש)
        return re.compile(r"(?<![א-ת])[והבלכש]{0,2}" + re.escape(t))
    return re.compile(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])")


def has(term: str, text: str) -> bool:
    """text חייב להיות מנורמל."""
    return bool(_pattern(term).search(text))


def hits(terms, text: str) -> List[str]:
    return [t for t in terms if has(t, text)]


_YEARS_RE = re.compile(
    r"(\d+)\s*\+?\s*(?:[-–]\s*\d+\s*)?(?:שנות|שנים|שנה|years?|yrs?)"
)


def _required_years(text: str) -> int:
    """שנות הניסיון המינימליות הנדרשות (0 אם לא נמצא או אם כתוב 'עד')."""
    best = 0
    for m in _YEARS_RE.finditer(text):
        window = text[max(0, m.start() - 45): m.end() + 45]
        if "ניסיון" not in window and "experience" not in window:
            continue
        before = text[max(0, m.start() - 9): m.start()]
        if "עד" in before or "up to" in before or "לכל היותר" in before:
            continue
        n = int(m.group(1))
        if n <= 20:
            best = max(best, n)
    return best


def _years_penalty(n: int) -> int:
    pen = 0
    for years, p in sorted(config.YEARS_PENALTY.items()):
        if n >= years:
            pen = p
    return pen


def score_job(job: Job) -> Tuple[int, List[str]]:
    title = norm(job.title)
    desc = norm(job.description)
    loc = norm(job.location)
    parts: List[Tuple[int, str]] = []   # (delta, reason)
    score = 0

    # --- התאמת תחום
    core_t = hits(config.TITLE_CORE_PR, title)
    comms_t = hits(config.TITLE_COMMS, title)
    core_d = hits(config.TITLE_CORE_PR, desc)
    comms_d = hits(config.TITLE_COMMS, desc)
    pr_signal = False
    if core_t:
        score += config.TITLE_CORE_WEIGHT
        parts.append((config.TITLE_CORE_WEIGHT, "כותרת תואמת יחסי ציבור/דוברות"))
        pr_signal = True
    elif comms_t:
        score += config.TITLE_COMMS_WEIGHT
        parts.append((config.TITLE_COMMS_WEIGHT, "כותרת בתחום תקשורת/תוכן"))
        pr_signal = True
    if core_d:
        score += config.DESC_CORE_WEIGHT
        parts.append((config.DESC_CORE_WEIGHT, "התיאור עוסק ביחסי ציבור/דוברות"))
        pr_signal = True
    elif comms_d:
        score += config.DESC_COMMS_WEIGHT
        parts.append((config.DESC_COMMS_WEIGHT, "התיאור כולל תקשורת/תוכן"))
        pr_signal = True

    # --- ג'וניור
    jr_t = hits(config.JUNIOR_TERMS, title)
    jr_d = hits(config.JUNIOR_TERMS, desc)
    if jr_t:
        score += config.JUNIOR_TITLE_WEIGHT
        parts.append((config.JUNIOR_TITLE_WEIGHT, "משרת כניסה/ג'וניור/סטודנט/רכז"))
    elif jr_d:
        score += config.JUNIOR_DESC_WEIGHT
        parts.append((config.JUNIOR_DESC_WEIGHT, "סימני התאמה למתחילים בתיאור"))

    # --- בכירות
    sr_t = hits(config.SENIOR_TERMS, title)
    if sr_t:
        score -= config.SENIOR_TITLE_PENALTY
        parts.append((-config.SENIOR_TITLE_PENALTY, "תפקיד בכיר (" + sr_t[0] + ")"))
    else:
        if hits(config.MANAGER_TERMS, title) and not hits(config.MANAGER_EXEMPT, title) \
                and not jr_t:
            score -= config.MANAGER_PENALTY
            parts.append((-config.MANAGER_PENALTY, "תפקיד ניהולי"))
        if hits(config.SENIOR_TERMS, desc):
            score -= config.SENIOR_DESC_PENALTY
            parts.append((-config.SENIOR_DESC_PENALTY, "התיאור מציין רמה בכירה"))
    years = _required_years(title + " . " + desc)
    pen = _years_penalty(years)
    if pen:
        score -= pen
        parts.append((-pen, "נדרשות %d+ שנות ניסיון" % years))

    # --- מיקום
    loc_all = loc
    remote = bool(hits(config.REMOTE_TERMS, loc + " " + title + " " + desc[:1500]))
    target = hits(config.TARGET_LOCATIONS, loc_all)
    if target:
        score += config.LOCATION_BONUS
        parts.append((config.LOCATION_BONUS, "מיקום באזור היעד"))
    elif remote:
        score += config.LOCATION_BONUS
        parts.append((config.LOCATION_BONUS, "היברידי/מרחוק"))
    elif hits(config.FAR_LOCATIONS, loc_all):
        score -= config.FAR_PENALTY
        parts.append((-config.FAR_PENALTY, "מיקום רחוק"))
    elif hits(config.OTHER_LOCATIONS, loc_all):
        score -= config.OTHER_PENALTY
        parts.append((-config.OTHER_PENALTY, "מחוץ לאזור היעד"))

    # --- בונוסים
    extras = [name for name, terms in config.EXTRAS.items()
              if hits(terms, title + " " + desc)]
    if extras:
        bonus = min(config.EXTRA_MAX, config.EXTRA_EACH * len(extras))
        score += bonus
        parts.append((bonus, "בונוס: " + ", ".join(extras[:3])))

    # --- שליליים
    neg_t = hits(config.NEGATIVE_TITLE_TERMS, title)
    if neg_t:
        score -= config.NEGATIVE_TITLE_PENALTY
        parts.append((-config.NEGATIVE_TITLE_PENALTY, "תחום לא רלוונטי (" + neg_t[0] + ")"))
    elif hits(config.NEGATIVE_DESC_TERMS, desc):
        score -= config.NEGATIVE_DESC_PENALTY
        parts.append((-config.NEGATIVE_DESC_PENALTY, "נראה כמוקד/מכירות"))

    if not pr_signal:
        score = min(score, config.NO_PR_SIGNAL_CAP)
    score = max(0, min(100, score))

    parts.sort(key=lambda p: -abs(p[0]))
    reasons = [r for _, r in parts[:4]]
    return score, reasons


def apply_score(job: Job) -> Job:
    job.score, job.reasons = score_job(job)
    return job
