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
# "דובר/ת רוסית/אוזבקית/..." = דובר שפה, לא דוברות. כל מילה שמסתיימת ב"ית" אחרי דובר = שפה.
_SPEAKER_LANG = re.compile(
    r"דובר(?:ת|ים|ות|י)?\s+(?:את\s+)?(?:ה|ו|ב)?(?:(?:" + _LANGS + r")|[א-ת]{2,}ית)(?![א-ת])"
    r"|(?:native\s+)?[a-z]+\s+speak(?:er|ing)s?")


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
    weak_t = hits(config.TITLE_WEAK, title)
    core_d = hits(config.TITLE_CORE_PR, desc)
    comms_d = hits(config.TITLE_COMMS, desc)
    pr_signal = False
    if core_t:
        score += config.TITLE_CORE_WEIGHT
        parts.append((config.TITLE_CORE_WEIGHT, "כותרת תואמת יח\"צ/דוברות/ייעוץ תקשורת"))
        pr_signal = True
    elif comms_t:
        score += config.TITLE_COMMS_WEIGHT
        parts.append((config.TITLE_COMMS_WEIGHT, "כותרת בתחום תקשורת/תוכן"))
        pr_signal = True
    elif weak_t:
        score += config.TITLE_WEAK_WEIGHT
        parts.append((config.TITLE_WEAK_WEIGHT, "המילה 'תקשורת' בכותרת"))
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
        if hits(config.SENIOR_TERMS, desc) and not jr_t:
            score -= config.SENIOR_DESC_PENALTY
            parts.append((-config.SENIOR_DESC_PENALTY, "התיאור מציין רמה בכירה"))
    years = _required_years(title + " . " + desc)
    pen = _years_penalty(years)
    if pen:
        score -= pen
        parts.append((-pen, "נדרשות %d+ שנות ניסיון" % years))

    # --- מיקום
    # סינון קשיח: מיקום ידוע שאינו באזור היעד -> מתחת לסף (אלא אם עבודה מהבית מלאה)
    loc_all = loc
    full_remote = bool(hits(config.FULL_REMOTE_TERMS, loc + " " + title + " " + desc[:1500]))
    target = hits(config.TARGET_LOCATIONS, loc_all)
    generic = (not loc_all) or bool(re.fullmatch(config.GENERIC_LOCATION_RE, loc_all))
    out_of_area = False
    if target:
        score += config.LOCATION_BONUS
        parts.append((config.LOCATION_BONUS, "מיקום באזור היעד"))
    elif full_remote:
        score += config.LOCATION_BONUS
        parts.append((config.LOCATION_BONUS, "עבודה מהבית"))
    elif not generic:
        out_of_area = True
        parts.append((-100, "מחוץ לאזור (" + (job.location or "")[:25] + ")"))

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
        # תחום לא רלוונטי בכותרת = פסילה (לא רק קנס)
        score = min(score - config.NEGATIVE_TITLE_PENALTY, config.NO_PR_SIGNAL_CAP)
        parts.append((-100, "תחום לא רלוונטי (" + neg_t[0] + ")"))
    elif hits(config.NEGATIVE_DESC_TERMS, desc):
        score -= config.NEGATIVE_DESC_PENALTY
        parts.append((-config.NEGATIVE_DESC_PENALTY, "נראה כמוקד/מכירות"))

    if not pr_signal or out_of_area:
        score = min(score, config.NO_PR_SIGNAL_CAP)
    score = max(0, min(100, score))

    parts.sort(key=lambda p: -abs(p[0]))
    reasons = [r for _, r in parts[:4]]
    return score, reasons


def apply_score(job: Job) -> Job:
    job.score, job.reasons = score_job(job)
    return job
