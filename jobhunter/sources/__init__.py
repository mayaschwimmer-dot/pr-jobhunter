"""רשימת מקורות. כל מקור חושף fetch() -> list[Job]."""
from . import (linkedin, drushim, alljobs, jobmaster, greenhouse, telegram,
               taasiya, ice, mploy, secrettlv, govo)

# (שם להצגה, פונקציית fetch) - לפי סדר עדיפות בדה-דופליקציה
SOURCES = [
    ("LinkedIn", linkedin.fetch),
    ("דרושים", drushim.fetch),
    ("אולג'ובס", alljobs.fetch),
    ("ג'ובמאסטר", jobmaster.fetch),
    ("Greenhouse", greenhouse.fetch),
    ("תעשיה", taasiya.fetch),
    ("אייס", ice.fetch),
    ("טלגרם", telegram.fetch),
    ("Mploy", mploy.fetch),
    ("Secret TLV", secrettlv.fetch),
    ("מכרזי רשויות", govo.fetch),
]
