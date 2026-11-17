' מפעיל את סריקת המשרות ב-GitHub (בלי חלון). רץ מ-Task Scheduler כל 10 דקות כשהמחשב דולק.
CreateObject("WScript.Shell").Run """C:\Program Files\GitHub CLI\gh.exe"" workflow run jobhunter.yml -R mayaschwimmer-dot/pr-jobhunter", 0, False
