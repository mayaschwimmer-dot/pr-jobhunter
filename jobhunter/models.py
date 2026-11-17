"""מודל נתונים למשרה."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Job:
    id: str                      # מזהה ייחודי כולל קידומת מקור, למשל "li:123456"
    source: str                  # שם המקור (LinkedIn / דרושים / ...)
    title: str
    company: str = ""
    location: str = ""
    url: str = ""
    posted_at: Optional[datetime] = None
    description: str = ""
    recruiter_name: str = ""
    recruiter_url: str = ""
    company_url: str = ""      # דף החברה בלינקדאין (אם ידוע)
    phones: List[str] = field(default_factory=list)
    # שדות עזר
    emails: List[str] = field(default_factory=list)
    posted_text: str = ""        # תיאור זמן כפי שמוצג באתר ("לפני 4 שעות")
    score: int = 0
    reasons: List[str] = field(default_factory=list)
