"""A small two-language layer (Hebrew / English).

English phrases are the keys; ``HEBREW`` holds their translations. This keeps the
project free of gettext tooling, so it runs anywhere Python runs.
"""

DEFAULT_LANGUAGE = "he"

HEBREW = {
    # navigation and general
    "Meeting scheduler": "מערכת שיבוץ פגישות",
    "Exhibitions": "תערוכות",
    "Log out": "יציאה",
    "Log in": "כניסה",
    "User name": "שם משתמש",
    "Password": "סיסמה",
    "Wrong user name or password.": "שם המשתמש או הסיסמה שגויים.",
    "Save": "שמירה",
    "Cancel": "ביטול",
    "Delete": "מחיקה",
    "Back": "חזרה",
    "Yes": "כן",
    "No": "לא",
    # exhibitions
    "New exhibition": "תערוכה חדשה",
    "Edit settings": "עריכת הגדרות",
    "No exhibitions yet.": "עדיין אין תערוכות.",
    "Name": "שם",
    "Meeting length (minutes)": "אורך פגישה (דקות)",
    "Seating": "מצב ישיבה",
    "Exhibitors seated, visitors move": "המציגים יושבים, המבקרים עוברים",
    "Visitors seated, exhibitors move": "המבקרים יושבים, המציגים עוברים",
    "Maximum meetings per visitor": "תקרת פגישות למבקר",
    "Leave empty for no limit.": "השאירו ריק אם אין תקרה.",
    "Time ranges": "טווחי שעות לפגישות",
    "A break is the gap between two ranges, for example 11:00–13:00 and 13:30–15:00.":
        "הפסקה היא הרווח בין שני טווחים, למשל \u206611:00–13:00\u2069 ואחריו \u206613:30–15:00\u2069.",
    "Date": "תאריך",
    "Start": "התחלה",
    "End": "סיום",
    "Remove": "הסרה",
    "The end time must be after the start time.": "שעת הסיום חייבת להיות אחרי שעת ההתחלה.",
    "Time ranges on the same day must not overlap.": "טווחי שעות באותו יום אינם יכולים לחפוף.",
    "Settings saved.": "ההגדרות נשמרו.",
    "The timetable is locked. Unlock it before changing settings.":
        "הלוח נעול. בטלו את הנעילה לפני שינוי ההגדרות.",
    "Changing the settings does not change existing meetings. Run the scheduling again to apply them.":
        "שינוי ההגדרות אינו משנה פגישות קיימות. הריצו שוב את השיבוץ כדי להחיל אותן.",
    # dashboard
    "Settings": "הגדרות",
    "Meeting slots": "חלונות זמן",
    "minutes": "דקות",
    "unused minutes at the end of the range": "דקות לא מנוצלות בסוף הטווח",
    "No time ranges defined yet.": "עדיין לא הוגדרו טווחי שעות.",
    "Step 1 – Participants file": "שלב 1 – קובץ משתתפים",
    "Step 2 – Requests file": "שלב 2 – קובץ בקשות",
    "Step 3 – Run the scheduling": "שלב 3 – הרצת השיבוץ",
    "Step 4 – Review and distribute": "שלב 4 – בדיקה והפצה",
    "Upload": "העלאה",
    "Download template": "הורדת תבנית",
    "Exhibitors": "מציגים",
    "Visitors": "מבקרים",
    "Requests": "בקשות",
    "Uploading a new participants file replaces the list and deletes the requests and the timetable.":
        "העלאת קובץ משתתפים חדש מחליפה את הרשימה ומוחקת את הבקשות ואת הלוח.",
    "Uploading a new requests file replaces the requests and deletes the timetable.":
        "העלאת קובץ בקשות חדש מחליפה את הבקשות ומוחקת את הלוח.",
    "Each visitor's requests are ranked by row order: the first row is the first priority.":
        "הבקשות של כל מבקר מדורגות לפי סדר השורות: השורה הראשונה היא העדיפות הראשונה.",
    "Supply (exhibitors × slots)": "היצע (מציגים × חלונות זמן)",
    "Demand (requests)": "ביקוש (בקשות)",
    "Exhibitors with more requests than slots": "מציגים שקיבלו יותר בקשות מחלונות זמן",
    "Suggested maximum per visitor": "תקרה מוצעת למבקר",
    "Run scheduling": "הרצת שיבוץ",
    "Running again replaces the whole timetable, including manual changes.":
        "הרצה חוזרת מחליפה את כל הלוח, כולל תיקונים ידניים.",
    "Results": "תוצאות",
    "Meetings scheduled": "פגישות ששובצו",
    "Requests granted": "בקשות שנענו",
    "Requests not granted": "בקשות שלא נענו",
    "Meetings per visitor (min / average / max)": "פגישות למבקר (מינימום / ממוצע / מקסימום)",
    "Meetings per exhibitor (min / average / max)": "פגישות למציג (מינימום / ממוצע / מקסימום)",
    "Visitors without any meeting": "מבקרים ללא אף פגישה",
    "View and edit timetable": "צפייה ועריכת הלוח",
    "Excel: full timetable and reports": "Excel: לוח מלא ודוחות",
    "PDF: personal schedules – visitors": "PDF: לוחות אישיים – מבקרים",
    "PDF: personal schedules – exhibitors": "PDF: לוחות אישיים – מציגים",
    "Lock timetable": "נעילת הלוח",
    "Unlock timetable": "ביטול נעילה",
    "Locked": "נעול",
    "The timetable is locked.": "הלוח נעול.",
    "The timetable is unlocked.": "הנעילה בוטלה.",
    "Scheduling finished.": "השיבוץ הושלם.",
    "participants imported.": "משתתפים נטענו.",
    "requests imported.": "בקשות נטענו.",
    "The file was not imported. Problems found:": "הקובץ לא נטען. נמצאו הבעיות הבאות:",
    "Row": "שורה",
    "Choose a file.": "בחרו קובץ.",
    "The timetable is locked. Unlock it before uploading files.":
        "הלוח נעול. בטלו את הנעילה לפני העלאת קבצים.",
    # importer messages
    "The file could not be read as an Excel (.xlsx) file.": "לא ניתן לקרוא את הקובץ כקובץ Excel (‎.xlsx).",
    "The file is empty.": "הקובץ ריק.",
    "The file has no data rows.": "אין בקובץ שורות נתונים.",
    "Missing column(s):": "חסרות עמודות:",
    "Missing ID.": "חסר מזהה.",
    "Duplicate ID:": "מזהה כפול:",
    "Type must be exhibitor or visitor:": "הסוג חייב להיות מציג או מבקר:",
    "Missing name.": "חסר שם.",
    "Table must be a number:": "מספר השולחן חייב להיות מספר:",
    "Visitor is not in the participants list:": "המבקר אינו ברשימת המשתתפים:",
    "Exhibitor is not in the participants list:": "המציג אינו ברשימת המשתתפים:",
    "Duplicate request:": "בקשה כפולה:",
    "Priority must be a positive number:": "העדיפות חייבת להיות מספר חיובי:",
    # scheduling errors
    "The timetable is locked. Unlock it before running again.": "הלוח נעול. בטלו את הנעילה לפני הרצה חוזרת.",
    "Define at least one time range before running.": "הגדירו לפחות טווח שעות אחד לפני ההרצה.",
    "Upload the requests file before running.": "העלו את קובץ הבקשות לפני ההרצה.",
    "A meeting needs one visitor and one exhibitor.": "פגישה מחייבת מבקר אחד ומציג אחד.",
    "These two already have a meeting.": "לשניים האלה כבר נקבעה פגישה.",
    "The visitor already has a meeting at that time.": "למבקר כבר יש פגישה בשעה זו.",
    "The exhibitor already has a meeting at that time.": "למציג כבר יש פגישה בשעה זו.",
    "The timetable is locked. Unlock it before editing.": "הלוח נעול. בטלו את הנעילה לפני עריכה.",
    "The scheduling engine could not find a solution in the time allowed.":
        "מנוע השיבוץ לא מצא פתרון בזמן שהוקצב.",
    # timetable
    "Timetable": "לוח הפגישות",
    "Show": "הצגה",
    "All participants": "כל המשתתפים",
    "Participant": "משתתף",
    "Time": "שעה",
    "Table": "שולחן",
    "Visitor": "מבקר",
    "Exhibitor": "מציג",
    "Company": "חברה",
    "Manual": "ידני",
    "Move": "הזזה",
    "Add a meeting": "הוספת פגישה",
    "Add": "הוספה",
    "Move meeting": "הזזת פגישה",
    "New time": "מועד חדש",
    "Meeting added.": "הפגישה נוספה.",
    "Meeting moved.": "הפגישה הוזזה.",
    "Meeting deleted.": "הפגישה נמחקה.",
    "No meetings to show.": "אין פגישות להצגה.",
    "Showing the first 500 meetings. Choose a participant to narrow the list.":
        "מוצגות 500 הפגישות הראשונות. בחרו משתתף כדי לצמצם את הרשימה.",
    # exports
    "Meetings": "פגישות",
    "Unmet requests": "בקשות שלא נענו",
    "Load": "עומס",
    "End time": "שעת סיום",
    "Visitor ID": "מזהה מבקר",
    "Visitor name": "שם מבקר",
    "Visitor company": "חברת מבקר",
    "Exhibitor ID": "מזהה מציג",
    "Exhibitor name": "שם מציג",
    "Exhibitor company": "חברת מציג",
    "Priority": "עדיפות",
    "ID": "מזהה",
    "Type": "סוג",
    "Requested": "בקשות",
    "Scheduled": "שובצו",
    "Email": 'דוא"ל',
    "Phone": "טלפון",
    "Personal meeting schedule": "לוח פגישות אישי",
    "Meeting with": "פגישה עם",
    "No meetings scheduled.": "לא נקבעו פגישות.",
    "visitor": "מבקר",
    "exhibitor": "מציג",
}


def tr(lang, text):
    """Translate an English phrase into the given language."""
    if lang == "he":
        return HEBREW.get(text, text)
    return text


def get_language(request):
    lang = request.session.get("lang", DEFAULT_LANGUAGE)
    return lang if lang in ("he", "en") else DEFAULT_LANGUAGE


def context(request):
    lang = get_language(request)
    return {"lang": lang, "direction": "rtl" if lang == "he" else "ltr"}
