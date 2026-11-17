' מפעיל את סריקת המשרות ב-GitHub (בלי חלון). רץ מ-Task Scheduler כל 10 דקות כשהמחשב דולק.
Set sh = CreateObject("WScript.Shell")
logf = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\pr-jobhunter-trigger.log"
sh.Run "cmd /c """"C:\Program Files\GitHub CLI\gh.exe"" workflow run jobhunter.yml -R mayaschwimmer-dot/pr-jobhunter > """ & logf & """ 2>&1""", 0, False
