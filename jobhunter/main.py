"""נקודת כניסה: מביא משרות מכל המקורות -> מסנן מה שנראה -> ניקוד -> מייל -> שמירת מצב.

הרצה:  python -m jobhunter.main [--dry-run] [--test-email]
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from . import config, emailer, state as state_mod
from .models import Job
from .scoring import apply_score, norm
from .sources import SOURCES, linkedin
from .sources.util import extract_emails, extract_phones, polite_sleep

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path) -> None:
    """טוען .env פשוט (KEY=VALUE) בלי לדרוס משתני סביבה קיימים."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ and v:
            os.environ[k] = v


def dedupe_key(job: Job) -> str:
    return "k:" + norm(job.title) + "|" + norm(job.company)


def fetch_all() -> List[Job]:
    jobs: List[Job] = []
    for name, fn in SOURCES:
        try:
            got = fn()
            print("[%s] %d משרות" % (name, len(got)))
            jobs.extend(got)
        except Exception as e:  # noqa: BLE001 - מקור שנכשל לא מפיל את ההרצה
            print("[%s] שגיאה: %s" % (name, str(e)[:200]))
    return jobs


def is_recent(job: Job, hours: int) -> bool:
    if job.posted_at is None:
        return True
    # לינקדאין נותן תאריך בלבד, לכן מרווח של יום נוסף
    slack = timedelta(hours=24) if job.source == "LinkedIn" else timedelta(0)
    return datetime.now() - job.posted_at <= timedelta(hours=hours) + slack


def print_ranking(scored: List[Job]) -> None:
    thr = config.SCORE_THRESHOLD
    matches = [j for j in scored if j.score >= thr]
    print("\n=== %d משרות מעל הסף (%d) מתוך %d חדשות ===" % (len(matches), thr, len(scored)))
    for j in matches[:15]:
        print("%3d | %s | %s | %s | %s" % (j.score, j.title[:50], j.company[:25],
                                          j.location[:25], j.source))
    if len(matches) > 20:
        print("  ... (תחתית הרשימה)")
        for j in matches[-5:]:
            print("%3d | %s | %s | %s" % (j.score, j.title[:50], j.company[:25], j.source))
    below = [j for j in scored if j.score < thr][:5]
    if below:
        print("--- הגבוהות מתחת לסף ---")
        for j in below:
            print("%3d | %s | %s | %s" % (j.score, j.title[:50], j.company[:25], j.source))


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description="התראות משרות יח\"צ")
    ap.add_argument("--dry-run", action="store_true", help="בלי מייל ובלי שמירת מצב; כותב out/preview.html")
    ap.add_argument("--test-email", action="store_true", help="שולח מייל לדוגמה לבדיקת הגדרות")
    args = ap.parse_args(argv)

    load_env(ROOT / ".env")
    preview_path = ROOT / config.PREVIEW_FILE
    state_path = ROOT / config.STATE_FILE

    if args.test_email:
        sample = Job(id="test:1", source="בדיקה", title="יחצן/ית ג'וניור (דוגמה)",
                     company="חברת דוגמה", location="הרצליה", url="https://www.linkedin.com/jobs/",
                     posted_text="לפני שעה", score=87,
                     reasons=["כותרת תואמת יחסי ציבור/דוברות", "משרת כניסה/ג'וניור", "מיקום באזור היעד"],
                     phones=["050-1234567"])
        html = emailer.build_html([sample])
        subject = "🔔 מייל בדיקה | " + emailer.build_subject([sample])
        if emailer.have_credentials():
            emailer.send(subject, html)
            print("נשלח מייל בדיקה.")
        else:
            p = emailer.write_preview(html, preview_path)
            print("חסרים GMAIL_USER / GMAIL_APP_PASSWORD / ALERT_TO - לא נשלח מייל. התצוגה נשמרה ב-%s" % p)
        return 0

    jobs = fetch_all()
    state = state_mod.prune(state_mod.load(state_path))
    first_run = not state
    now_iso = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")

    # --- דה-דופליקציה: מול המצב ובתוך ההרצה (מזהה + כותרת/חברה)
    new_jobs: List[Job] = []
    run_keys = set()
    for j in jobs:
        key = dedupe_key(j)
        if j.id in state or key in state or key in run_keys:
            continue
        run_keys.add(key)
        new_jobs.append(j)
    print("חדשות (לא נראו קודם): %d מתוך %d" % (len(new_jobs), len(jobs)))

    for j in new_jobs:
        apply_score(j)
    new_jobs.sort(key=lambda j: -j.score)
    thr = config.SCORE_THRESHOLD
    matches = [j for j in new_jobs if j.score >= thr]

    # --- הרצה ראשונה: רק הטובות מה-24 שעות האחרונות
    candidates = matches
    if first_run and not args.dry_run:
        candidates = [j for j in matches if is_recent(j, config.FIRST_RUN_HOURS)][:config.FIRST_RUN_MAX]
        print("הרצה ראשונה: הכל יסומן כנראה, במייל עד %d משרות." % len(candidates))

    # --- העשרה (לינקדאין): תיאור + מגייס, ואז ניקוד מחדש
    enriched = 0
    for j in candidates:
        if j.source == "LinkedIn" and enriched < config.MAX_ENRICH_PER_RUN:
            try:
                polite_sleep()
                if linkedin.enrich(j):
                    apply_score(j)
                enriched += 1
            except Exception as e:  # noqa: BLE001
                print("  העשרה נכשלה (%s): %s" % (j.id, str(e)[:100]))
        if not j.phones:
            j.phones = extract_phones(j.description)
        if not j.emails:
            j.emails = extract_emails(j.description)
    candidates = sorted((j for j in candidates if j.score >= thr), key=lambda j: -j.score)

    if args.dry_run:
        print_ranking(sorted(new_jobs, key=lambda j: -j.score))

    sent = False
    if candidates:
        html = emailer.build_html(candidates)
        subject = emailer.build_subject(candidates)
        if args.dry_run:
            p = emailer.write_preview(html, preview_path)
            print("\n[dry-run] %d משרות במייל. תצוגה: %s (לא נשלח, מצב לא נשמר)" % (len(candidates), p))
        elif not emailer.have_credentials():
            p = emailer.write_preview(html, preview_path)
            print("\nחסרים GMAIL_USER / GMAIL_APP_PASSWORD / ALERT_TO - לא נשלח מייל; "
                  "התצוגה נשמרה ב-%s. המצב לא נשמר כדי שלא תפספסו משרות." % p)
            return 0
        else:
            try:
                emailer.send(subject, html)
                sent = True
                print("\nנשלח מייל עם %d משרות." % len(candidates))
            except Exception as e:  # noqa: BLE001
                print("\nשליחת המייל נכשלה: %s - המשרות לא יסומנו כנראו ויישלחו בהרצה הבאה." % e)
                return 1
    else:
        print("\nאין משרות חדשות מתאימות.")

    if args.dry_run:
        return 0

    # --- שמירת מצב: כל המשרות החדשות מסומנות כנראו (כשל בשליחה כבר יצא מוקדם)
    for j in new_jobs:
        state[j.id] = now_iso
        state[dedupe_key(j)] = now_iso
    state_mod.save(state_path, state)
    print("מצב נשמר (%d רשומות)." % len(state))
    return 0


if __name__ == "__main__":
    sys.exit(main())
