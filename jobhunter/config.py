"""הגדרות הכלי - כאן עורכים מילות מפתח, משקלים וסף התראה.

כל המונחים נבדקים אחרי נרמול: אותיות קטנות, בלי גרשיים/גרשיים כפולים
(יח"צ -> יחצ, ג'וניור -> גוניור) ובלי סיומות מגדר כמו "/ת" (דובר/ת -> דובר).
מונחים בעברית מתאימים גם עם תחיליות (ל/ב/ה/ו/כ/ש) ועם סיומות.
מונחים באנגלית מתאימים כמילה שלמה.
"""

# ---------------------------------------------------------------- כללי
SCORE_THRESHOLD = 40         # סף ציון להתראה (0..100)
FIRST_RUN_MAX = 15            # בהרצה ראשונה: מקסימום משרות במייל
FIRST_RUN_HOURS = 24          # ...ורק מה-24 שעות האחרונות
STATE_MAX_AGE_DAYS = 45       # כמה זמן לזכור משרה שנראתה
REQUEST_TIMEOUT = 15          # שניות
REQUEST_DELAY = 1.5           # השהיה מנומסת בין בקשות (שניות)
MAX_ENRICH_PER_RUN = 20       # כמה משרות לינקדאין להעשיר בפרטים בכל הרצה

# ---------------------------------------------------------------- חיפושים
# שאילתות ללינקדאין (ציבורי, ללא התחברות)
# מאוחד עם OR כדי לשלוח מעט בקשות (לינקדאין חוסם שרתי GitHub על ריבוי בקשות - 429)
LINKEDIN_QUERIES = [
    'יחסי ציבור OR יח"צ OR דוברות OR דובר OR דוברת OR "קשרי תקשורת"',
    '"public relations" OR "media relations" OR spokesperson OR "PR coordinator"',
    '"PR account" OR "PR intern" OR "communications coordinator" OR "PR associate"',
    '"קשרי קהילה" OR "שיתוף ציבור" OR "ליווי ציבורי" OR "community relations" OR "community engagement"',
]
LINKEDIN_TIME_FILTER = "r86400"   # 24 שעות אחרונות (r3600=שעה, r604800=שבוע)

# שאילתות לאתרי דרושים / אולג'ובס / ג'ובמאסטר
BOARD_QUERIES = ["יחסי ציבור", "יחצ", "דוברות", "דובר", "תקשורת", "קשרי עיתונאים",
                 "קשרי קהילה", "שיתוף ציבור"]

# לוחות Greenhouse ציבוריים של חברות ישראליות גדולות (slug -> שם תצוגה).
# מוסיפים בקלות: slug מופיע ב-boards.greenhouse.io/<slug>
GREENHOUSE_BOARDS = {
    "riskified": "Riskified", "taboola": "Taboola", "payoneer": "Payoneer",
    "similarweb": "Similarweb", "gongio": "Gong", "pagaya": "Pagaya",
    "jfrog": "JFrog", "nice": "NICE", "forter": "Forter",
    "yotpo": "Yotpo", "appsflyer": "AppsFlyer",
    "wizinc": "Wiz", "axonius": "Axonius", "orcasecurity": "Orca Security",
    "via": "Via",
}
# מהמשרות בלוחות האלה נשארות רק כאלה שהכותרת שלהן מכילה אחד מהמונחים (סינון מקדים)
BOARD_TITLE_PREFILTER = [
    "pr", "public relations", "communications", "communication", "comms",
    "media", "press", "spokes", "content", "social", "brand", "יחצ",
    "יחסי ציבור", "דובר", "תקשורת", "תוכן", "community", "קהילה", "שיתוף ציבור",
]

# ---------------------------------------------------------------- מקורות נוספים
# ערוצי טלגרם ציבוריים (תצוגת web ללא התחברות: t.me/s/<ערוץ>) -> שם תצוגה
TELEGRAM_CHANNELS = {
    "israel_media_industry": "אנדר קונטרול - דרושים בתקשורת",
    "TheMisrot": "משרות - ביטחון וממשל",
    "PMO_jobs": "משרד ראש הממשלה - דרושים",
}
TELEGRAM_MAX_AGE_DAYS = 14     # פוסטים ישנים יותר - מתעלמים
BOARD_MAX_AGE_DAYS = 30        # לוחות בלי תפוגה (תעשיה וכד') - משרות ישנות מתעלמים
EXTRA_PAGES = 2                # דרושים / אולג'ובס: כמה עמודי תוצאות לכל שאילתה

# סינון מקדים למקורות רחבים (טלגרם, לוחות מדיה, מכרזי רשויות): נשארות רק משרות
# שבכותרת/בטקסט יש להן אחד המונחים. בלי זה כל פוסט היה נכנס לניקוד כרעש.
PR_PREFILTER = [
    "יחסי ציבור", "יחצ", "יחצן", "יחצנית", "דוברות", "דובר", "דוברת", "תקשורת",
    "קשרי עיתונות", "קשרי ממשל", "קשרי קהילה", "קישרי קהילה", "שיתוף ציבור",
    "ליווי ציבורי", "הסברה", "community relations", "community engagement",
    "public relations", "media relations", "spokes", "communications",
    "communication", "comms", "pr", "press", "publicist", "public affairs",
    "קופירייטר", "סושיאל", "social media", "content", "תוכן",
]

# ---------------------------------------------------------------- ניקוד
# כותרת - ליבת יחסי ציבור / דוברות
TITLE_CORE_PR = [
    "יחסי ציבור", 'יח"צ', "יחצ", "יחצן", "יחצנית", "דוברות", "דובר", "דוברת",
    "קשרי עיתונות", "קשרי תקשורת", "פרסום וקשרי ציבור",
    "public relations", "media relations", "spokesperson", "spokesman",
    "pr", "press", "publicist", "public affairs",
    # ייעוץ תקשורת = תפקיד ליבה (ייעוץ תקשורתי/אסטרטגי במשרדי יח"צ)
    "יועץ תקשורת", "יועצת תקשורת", "יועצ תקשורת", "יועצי תקשורת", "ייעוץ תקשורת",
    "ייעוץ תקשורתי", "יועץ תקשורתי", "יועצת תקשורתית", "communications consultant",
    "communication consultant", "media consultant", "יועץ מדיה", "יועצת מדיה",
    # קשרי קהילה ושיתוף ציבור = תפקיד ליבה (בין דוברות ליח"צ, למשל שילובים, CR קשרי קהילה)
    "קשרי קהילה", "קישרי קהילה", "שיתוף ציבור", "שיתוף הציבור", "ליווי ציבורי",
    "הסברה", "community relations", "community engagement", "public engagement",
    "public participation",
]
TITLE_CORE_WEIGHT = 50

# כותרת - תקשורת / תוכן קרוב ליח"צ
TITLE_COMMS = [
    # "תקשורת" לבד מביא טלקום/IT/קלינאות - לכן רק צירופים שמעידים על תקשורת-יח"צ
    "תחום תקשורת",
    "תחום התקשורת", "מחלקה לתקשורת", "מחלקת תקשורת", "תקשורת שיווקית", "תקשורת ודוברות",
    "תקשורת ויחסי", "תקשורת פנים", "תקשורת תאגידית", "רכז תקשורת", "רכזת תקשורת",
    "תוכן", "סושיאל", "רשתות חברתיות", "קופירייטר", "כתב", "עורך",
    "communications", "communication", "comms", "content", "social media",
    "copywriter", "corporate affairs", "editor", "writer",
]
TITLE_COMMS_WEIGHT = 28

# "תקשורת" לבד בכותרת - סימן חלש בלבד (לא מספיק לבד כדי לעבור את הסף)
TITLE_WEAK = ["תקשורת"]
TITLE_WEAK_WEIGHT = 10

# תיאור המשרה
DESC_CORE_WEIGHT = 12        # אם מופיע מונח ליבה בתיאור
DESC_COMMS_WEIGHT = 6        # אם מופיע רק מונח תקשורת

# סימני ג'וניור
JUNIOR_TERMS = [
    "ג'וניור", "junior", "jr", "entry", "entry level", "סטודנט", "סטודנטית",
    "משרת סטודנט", "התמחות", "מתמחה", "intern", "internship", "ללא ניסיון",
    "ללא ניסיון קודם", "עד שנתיים", "coordinator", "רכז", "רכזת",
    "assistant", "עוזר", "עוזרת", "associate", "trainee", "מתחיל",
]
JUNIOR_TITLE_WEIGHT = 15
JUNIOR_DESC_WEIGHT = 7

# סימני בכירות (קנס)
SENIOR_TERMS = [
    "senior", "sr", "בכיר", "בכירה", "head of", "vp", "vice president",
    "director", "מנהל מחלקה", "מנהלת מחלקה", "ראש תחום", "ראש צוות",
    "ראש אגף", "סמנכל", "lead", "chief", "principal",
]
SENIOR_TITLE_PENALTY = 35
SENIOR_DESC_PENALTY = 12        # מונח בכירות בתיאור (פחות חמור)
# קנס "מנהל/ת" בכותרת (תפקיד ניהולי), לא חל על account manager
MANAGER_TERMS = ["מנהל", "מנהלת", "manager"]
MANAGER_EXEMPT = ["account manager", "אקאונט מנג'ר", "office manager",
                  "מנהל פרויקט", "מנהלת פרויקט", "מנהל פרויקטים", "project manager"]
MANAGER_PENALTY = 15
# קנס לפי שנות ניסיון נדרשות: {שנים מינימליות: קנס}
YEARS_PENALTY = {3: 20, 4: 28, 5: 35}

# מיקום
TARGET_LOCATIONS = [
    "tel aviv", "תל אביב", "ramat gan", "רמת גן", "givatayim", "גבעתיים",
    "petah tikva", "petach tikva", "פתח תקווה", "bnei brak", "בני ברק",
    "holon", "חולון", "bat yam", "בת ים", "rishon", "ראשון לציון",
    "or yehuda", "אור יהודה", "herzliya", "הרצליה", "ramat hasharon",
    "רמת השרון", "raanana", "רעננה", "kfar saba", "כפר סבא", "hod hasharon",
    "הוד השרון", "netanya", "נתניה", "gush dan", "גוש דן", "sharon", "השרון",
    "center district", "מחוז המרכז", "מחוז תל אביב",
]
# עבודה מהבית מלאה - רק זה עוקף את סינון המיקום (היברידי עדיין דורש הגעה)
FULL_REMOTE_TERMS = ["remote", "fully remote", "עבודה מהבית", "עבודה מרחוק", "מהבית"]
# מיקום כללי (לא ידוע) - לא נפסל
GENERIC_LOCATION_RE = (r"[\s,|·-]*(?:(?:israel|ישראל|מרכז|אזור המרכז|כל הארץ|center|central|district|"
                       r"מספר מקומות|גמיש|hybrid|היברידי|on-site|on site)[\s,|·()-]*)*")
REMOTE_TERMS =["hybrid", "remote", "היברידי", "עבודה מהבית", "עבודה מרחוק", "היברידית"]
FAR_LOCATIONS = [
    "haifa", "חיפה", "beer sheva", "באר שבע", "eilat", "אילת", "north", "צפון",
    "south", "דרום", "kiryat shmona", "קריית שמונה", "tiberias", "טבריה",
    "afula", "עפולה", "nazareth", "נצרת", "karmiel", "כרמיאל", "ashkelon",
    "אשקלון", "ashdod", "אשדוד", "dimona", "דימונה", "arad", "ערד",
]
LOCATION_BONUS = 8
FAR_PENALTY = 15
OTHER_PENALTY = 5          # ירושלים וכד' - מחוץ לאזור היעד אך לא רחוק מאוד
OTHER_LOCATIONS = ["jerusalem", "ירושלים"]

# בונוסים לתכונות רלוונטיות (+2 לכל אחת, עד תקרה)
EXTRAS = {
    "דיגיטל": ["digital", "דיגיטל"],
    "סושיאל": ["social media", "סושיאל", "רשתות חברתיות"],
    "תוכן": ["content", "תוכן"],
    "הפקה": ["production", "הפקה"],
    "Canva": ["canva", "קנבה"],
    "עברית+אנגלית": ["אנגלית", "english"],
}
EXTRA_EACH = 2
EXTRA_MAX = 8

# שליליים בכותרת (קנס)
NEGATIVE_TITLE_TERMS = [
    "מכירות", "מכירה", "sales", "שירות לקוחות", "customer service", "telemarketing", "טלמרקטינג", "מוקדן", "מוקד", "call center",
    "נציג", "נציגת", "graphic designer", "מעצב גרפי", "מעצבת גרפית", "מעצב",
    "developer", "מפתח", "מפתחת", "engineer", "מהנדס", "מהנדסת", "נהג",
    "חשבונאי", "הנהלת חשבונות", "קופאי", "מלצר",
    "טכנאי", "טכנאית", "technician", "מכרז", "מזכיר רפואי",
    # "תקשורת" במובן טלקום/קלינאות - לא יח"צ
    "קלינאי", "קלינאית", "קלינאות", "מערכות תקשורת", "תשתיות תקשורת", "רשתות תקשורת",
    "תקשורת נתונים", "טכנאי תקשורת", "מתקין", "סיבים", "noc", "presale", "pre-sale",
    "פריסייל", "back office", "בק אופיס", "network", "telecom", "סלולר",
    "ורשתות", "אבטחת מידע", "תומך טכני", "תומכת טכנית", "תמיכה טכנית", "help desk",
    "גני תקשורת", "גננת", "גננות", "סייעת", "מאבטח", "מאבטחים", "אנשי שירות",
    "חברת תקשורת", "פתרונות תקשורת", "it",
    "עורך דין", "עורכת דין", "lawyer", "attorney", "legal counsel", "paralegal",
]
NEGATIVE_TITLE_PENALTY = 30
# שליליים בתיאור
NEGATIVE_DESC_TERMS = ["מוקד טלפוני", "call center", "telemarketing", "מכירות טלפוניות"]
NEGATIVE_DESC_PENALTY = 10

# בלי שום סימן לתחום יחסי ציבור/תקשורת - תקרת ציון
NO_PR_SIGNAL_CAP = 20

# ---------------------------------------------------------------- קבצים
STATE_FILE = "data/seen.json"
PREVIEW_FILE = "out/preview.html"
