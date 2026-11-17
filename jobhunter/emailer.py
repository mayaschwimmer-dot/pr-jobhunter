"""בניית מייל HTML בעברית (RTL) ושליחה דרך Gmail SMTP SSL."""
from __future__ import annotations

import os
import re
import smtplib
from datetime import datetime
from email.message import EmailMessage
from html import escape
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

from .models import Job


def have_credentials() -> bool:
    return all(os.environ.get(k) for k in ("GMAIL_USER", "GMAIL_APP_PASSWORD", "ALERT_TO"))


def _badge_color(score: int) -> str:
    if score >= 75:
        return "#1e8e3e"
    if score >= 60:
        return "#f29900"
    return "#5f6368"


def recruiter_search_url(company: str) -> str:
    q = '%s (recruiter OR HR OR גיוס OR "talent acquisition" OR "משאבי אנוש")' % company
    return "https://www.linkedin.com/search/results/people/?keywords=" + quote(q)


def company_search_url(company: str) -> str:
    return "https://www.linkedin.com/search/results/companies/?keywords=" + quote(company)


def company_jobs_url(company: str) -> str:
    return "https://www.linkedin.com/jobs/search/?keywords=" + quote(company)


def _posted(job: Job) -> str:
    if job.posted_text:
        return job.posted_text
    if job.posted_at:
        return job.posted_at.strftime("%d/%m/%Y %H:%M")
    return "לא ידוע"


def _contact_html(job: Job) -> str:
    rows = []
    if job.recruiter_name:
        name = escape(job.recruiter_name)
        if job.recruiter_url:
            rows.append('<div><b>👤 המגייס/ת שפרסמ/ה את המשרה: <a href="%s" style="color:#0a66c2">%s</a></b></div>'
                        % (escape(job.recruiter_url, True), name))
        else:
            rows.append("<div><b>👤 המגייס/ת: %s</b></div>" % name)
    if job.company_url:
        # דף "אנשים" של החברה בלינקדאין, מסונן - מציג רק עובדי החברה עצמה
        base = job.company_url.rstrip("/") + "/people/?keywords="
        rows.append(
            '<div>🔎 בחברה עצמה: <a href="%s" style="color:#0a66c2">מגייסים</a>'
            ' &nbsp;|&nbsp; <a href="%s" style="color:#0a66c2">משאבי אנוש / גיוס</a>'
            ' &nbsp;|&nbsp; <a href="%s" style="color:#0a66c2">Talent Acquisition</a></div>'
            % (escape(base + quote("recruiter"), True), escape(base + quote("גיוס"), True),
               escape(base + quote("talent acquisition"), True)))
    if job.phones:
        rows.append("<div>טלפון: %s</div>" % " , ".join(
            '<a href="tel:%s" style="color:#0a66c2">%s</a>' % (escape(p, True), escape(p))
            for p in job.phones))
    if job.emails:
        rows.append("<div>מייל: %s</div>" % " , ".join(
            '<a href="mailto:%s" style="color:#0a66c2">%s</a>' % (escape(e, True), escape(e))
            for e in job.emails))
    if job.source == "אולג'ובס":
        # הגשה דרך אולג'ובס דורשת לעיתים מנוי VIP - קישורים למציאת אותה משרה במקום חינמי
        t = re.sub(r"\s*/\s*(?:ית|ת|ה)\b", "", job.title)
        t = re.sub(r"^(?:דרוש(?:ים|ה|ות)?\s*)", "", t).strip()
        comp = job.company if job.company and "חסוי" not in job.company else ""
        g = quote('"%s" %s -alljobs' % (t[:60], comp))
        li = quote(t[:60])
        rows.append(
            '<div style="background:#fff8e1;padding:6px 8px;border-radius:6px;margin-top:4px">'
            '💡 אולג\'ובס עשוי לדרוש מנוי VIP להגשה. אותה משרה במקום אחר: '
            '<a href="https://www.google.com/search?q=%s" style="color:#0a66c2">גוגל</a>'
            ' &nbsp;|&nbsp; <a href="https://www.linkedin.com/jobs/search/?keywords=%s&location=Israel" style="color:#0a66c2">לינקדאין</a>'
            ' &nbsp;|&nbsp; <a href="https://www.drushim.co.il/jobs/search/%s/" style="color:#0a66c2">דרושים</a></div>'
            % (g, li, li))
    company = job.company
    if company and "חסוי" not in company:
        rows.append(
            '<div><a href="%s" style="color:#0a66c2">חיפוש גיוס/HR בחברה בלינקדאין</a>'
            ' &nbsp;|&nbsp; <a href="%s" style="color:#0a66c2">דף החברה</a>'
            ' &nbsp;|&nbsp; <a href="%s" style="color:#0a66c2">משרות נוספות בחברה</a></div>'
            % (escape(recruiter_search_url(company), True),
               escape(company_search_url(company), True),
               escape(company_jobs_url(company), True)))
    return "".join(rows)


def _card(job: Job) -> str:
    color = _badge_color(job.score)
    reasons = "".join("<li>%s</li>" % escape(r) for r in job.reasons)
    meta = " &middot; ".join(escape(x) for x in (job.company, job.location) if x)
    return """
<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #e0e0e0;border-radius:10px;margin:0 0 14px 0">
<tr><td style="padding:14px 16px" dir="rtl">
  <table role="presentation" width="100%%" cellpadding="0" cellspacing="0"><tr>
    <td style="font-size:17px;font-weight:bold;color:#202124;text-align:right">%(title)s</td>
    <td width="70" style="text-align:left;vertical-align:top"><span style="display:inline-block;background:%(color)s;color:#fff;border-radius:14px;padding:3px 10px;font-size:13px;font-weight:bold;white-space:nowrap" dir="ltr">%(score)d/100</span></td>
  </tr></table>
  <div style="font-size:14px;color:#3c4043;margin-top:4px">%(meta)s</div>
  <div style="font-size:12px;color:#80868b;margin-top:2px">מקור: %(source)s &middot; פורסם: %(posted)s</div>
  <ul style="margin:8px 18px 8px 0;padding:0 18px 0 0;font-size:13px;color:#3c4043">%(reasons)s</ul>
  <div style="margin:10px 0"><a href="%(url)s" style="display:block;background:#0a66c2;color:#ffffff;text-decoration:none;text-align:center;padding:12px 10px;border-radius:8px;font-size:16px;font-weight:bold">לעמוד המשרה</a></div>
  <div style="font-size:13px;color:#3c4043;border-top:1px solid #eee;padding-top:8px;line-height:1.7">%(contact)s</div>
</td></tr></table>""" % {
        "title": escape(job.title), "color": color, "score": job.score,
        "meta": meta, "source": escape(job.source), "posted": escape(_posted(job)),
        "reasons": reasons, "url": escape(job.url, True), "contact": _contact_html(job),
    }


def build_subject(jobs: List[Job]) -> str:
    top = max(j.score for j in jobs)
    n = len(jobs)
    word = "משרת יח\"צ חדשה" if n == 1 else "משרות יח\"צ חדשות"
    return "🔔 %d %s | הכי גבוהה: %d/100" % (n, word, top)


def build_html(jobs: List[Job]) -> str:
    cards = "".join(_card(j) for j in jobs)
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    return """<!DOCTYPE html>
<html dir="rtl" lang="he"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>התראת משרות</title></head>
<body dir="rtl" style="margin:0;padding:0;background:#f1f3f4;font-family:Arial,'Segoe UI',Helvetica,sans-serif">
<table role="presentation" width="100%%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:12px">
<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" style="max-width:640px">
<tr><td dir="rtl" style="padding:6px 4px 14px 4px;text-align:right">
  <div style="font-size:22px;font-weight:bold;color:#202124">נמצאו %(n)d משרות חדשות בתחום יחסי ציבור ותקשורת</div>
  <div style="font-size:12px;color:#80868b">%(now)s &middot; ממוין לפי ציון התאמה</div>
  <div style="font-size:12px;color:#80868b;margin-top:4px">מקרא: 75+ = יח"צ/דוברות/ייעוץ תקשורת + ג'וניור + באזור &middot; 55–74 = אותם תפקידים באזור, בלי סימני ג'וניור &middot; 40–54 = תפקיד קרוב (תוכן, סושיאל, ניהול)</div>
</td></tr>
<tr><td>%(cards)s</td></tr>
<tr><td dir="rtl" style="font-size:11px;color:#80868b;text-align:center;padding:8px">הציון מחושב לפי מילות מפתח וכללים בלבד. הקישורים לחיפוש אנשי גיוס הם קישורי חיפוש ציבוריים בלינקדאין.</td></tr>
</table></td></tr></table></body></html>""" % {"n": len(jobs), "now": now, "cards": cards}


def write_preview(html: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


def send(subject: str, html: str, text: Optional[str] = None) -> None:
    user = os.environ["GMAIL_USER"]
    pw = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "").replace(" ", "").strip()
    to = os.environ["ALERT_TO"]
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to
    msg.set_content(text or "המייל מכיל תוכן HTML. פתחו אותו בתוכנת דואר התומכת ב-HTML.")
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(user, pw.replace(" ", ""))
        s.send_message(msg)
