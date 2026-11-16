"""רשימת מקורות. כל מקור חושף fetch() -> list[Job]."""
from . import linkedin, drushim, alljobs, jobmaster, greenhouse

# (שם להצגה, פונקציית fetch) - לפי סדר עדיפות בדה-דופליקציה
SOURCES = [
    ("LinkedIn", linkedin.fetch),
    ("דרושים", drushim.fetch),
    ("אולג'ובס", alljobs.fetch),
    ("ג'ובמאסטר", jobmaster.fetch),
    ("Greenhouse", greenhouse.fetch),
]
