"""Reading and validating the two Excel files the organiser uploads.

Both imports are all-or-nothing: if any row is wrong, nothing is saved and the
organiser gets the full list of problems. Real-world files are untidy, so the
reader is forgiving about layout (title rows above the header, extra columns,
different spellings of the headers, upper/lower case in IDs) and strict about
content (unknown IDs, missing names).
"""
from django.db import transaction
from openpyxl import load_workbook

from .models import Meeting, MeetingRequest, Participant

# Accepted header names (lower-cased) for each field, in English and Hebrew.
PARTICIPANT_HEADERS = {
    "code": ["id", "code", "participant id", "participant_id", "מזהה", "מזהה משתתף", "קוד", "קוד משתתף",
             "מספר", "מספר משתתף", "מס'"],
    "kind": ["type", "kind", "role", "participant type", "סוג", "סוג משתתף", "תפקיד"],
    "name": ["name", "full name", "שם", "שם מלא", "שם נציג", "שם הנציג", "שם המשתתף", "שם משתתף"],
    "company": ["company", "organization", "organisation", "חברה", "שם חברה", "שם החברה", "ארגון"],
    "email": ["email", "e-mail", "mail", 'דוא"ל', "דואל", "דוא״ל", "אימייל", "מייל", "דואר אלקטרוני"],
    "phone": ["phone", "mobile", "telephone", "טלפון", "נייד", "טלפון נייד"],
    "table": ["table", "table number", "שולחן", "מספר שולחן", "מס' שולחן"],
}
REQUEST_HEADERS = {
    "visitor": ["visitor_id", "visitor id", "visitor", "buyer", "buyer id", "מזהה מבקר", "מבקר", "קוד מבקר",
                "מספר מבקר"],
    "exhibitor": ["exhibitor_id", "exhibitor id", "exhibitor", "supplier", "מזהה מציג", "מציג", "קוד מציג",
                  "מספר מציג"],
    "rank": ["priority", "rank", "עדיפות", "דירוג"],
}
# What to call each column when telling the organiser it is missing.
COLUMN_LABELS = {
    "code": "מזהה / id", "kind": "סוג / type", "name": "שם / name",
    "visitor": "מזהה מבקר / visitor_id", "exhibitor": "מזהה מציג / exhibitor_id",
}
KIND_WORDS = {
    **dict.fromkeys(["exhibitor", "exhibitors", "supplier", "seller", "מציג", "מציגה", "מציגים", "ספק"],
                    Participant.EXHIBITOR),
    **dict.fromkeys(["visitor", "visitors", "buyer", "מבקר", "מבקרת", "מבקרים", "קניין", "קונה"],
                    Participant.VISITOR),
}
MAX_LENGTH = {"code": 50, "name": 200, "company": 200, "email": 200, "phone": 50}
MAX_TABLE = 100000
HEADER_SEARCH_ROWS = 10


class ImportErrors(Exception):
    """Raised with a list of (row_number, message_key, detail) tuples."""

    def __init__(self, errors):
        super().__init__(f"{len(errors)} import errors")
        self.errors = errors


def _text(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return " ".join(str(value).split())


def normalise(code):
    """IDs are compared without regard to upper/lower case or surrounding spaces."""
    return _text(code).casefold()


def _load_rows(file):
    try:
        sheet = load_workbook(file, data_only=True).active
        return [[_text(cell) for cell in row] for row in sheet.iter_rows(values_only=True)]
    except Exception as exc:  # not a readable .xlsx file
        raise ImportErrors([(0, "The file could not be read as an Excel (.xlsx) file.", "")]) from exc


def _read_rows(file, headers, required):
    """Return (data, extra_columns).

    ``data`` is a list of (row_number, {field: text}, [extra cell texts]). The header row
    is the first of the top rows that contains the required columns, so title rows above
    it are fine.
    """
    rows = _load_rows(file)
    if not any(any(row) for row in rows):
        raise ImportErrors([(0, "The file is empty.", "")])

    best = None  # (number of required columns found, row index, columns)
    for index, row in enumerate(rows[:HEADER_SEARCH_ROWS]):
        names = [cell.lower() for cell in row]
        columns = {}
        for field, accepted in headers.items():
            for position, name in enumerate(names):
                if name in accepted:
                    columns[field] = position
                    break
        found = sum(1 for field in required if field in columns)
        if best is None or found > best[0]:
            best = (found, index, columns)
        if found == len(required):
            break
    _found, header_index, columns = best
    missing = [COLUMN_LABELS[field] for field in required if field not in columns]
    if missing:
        raise ImportErrors([(header_index + 1, "Missing column(s):", ", ".join(missing))])

    used = set(columns.values())
    data = []
    for number, row in enumerate(rows[header_index + 1:], start=header_index + 2):
        record = {f: row[i] if i < len(row) else "" for f, i in columns.items()}
        extras = [cell for i, cell in enumerate(row) if i not in used and cell]
        if any(record.values()) or extras:
            data.append((number, record, extras))
    return data


@transaction.atomic
def import_participants(exhibition, file):
    """Replace the exhibition's participants. Removes existing requests and meetings."""
    rows = _read_rows(file, PARTICIPANT_HEADERS, required=["code", "kind", "name"])
    errors, seen, participants = [], set(), []
    for number, record, _extras in rows:
        code = record["code"]
        if not code:
            errors.append((number, "Missing ID.", ""))
            continue
        if normalise(code) in seen:
            errors.append((number, "Duplicate ID:", code))
            continue
        seen.add(normalise(code))
        kind = KIND_WORDS.get(record["kind"].lower())
        if kind is None:
            errors.append((number, "Type must be exhibitor or visitor:", record["kind"]))
            continue
        if not record["name"]:
            errors.append((number, "Missing name.", ""))
            continue
        too_long = [f for f, limit in MAX_LENGTH.items() if len(record.get(f, "")) > limit]
        if too_long:
            field = too_long[0]
            errors.append((number, "Text is too long:", f"{record[field][:40]}… (max {MAX_LENGTH[field]})"))
            continue
        table = None
        if record.get("table"):
            if not record["table"].isdigit() or not 1 <= int(record["table"]) <= MAX_TABLE:
                errors.append((number, "Table must be a number:", record["table"]))
                continue
            table = int(record["table"])
        participants.append(
            Participant(
                exhibition=exhibition,
                code=code,
                kind=kind,
                name=record["name"],
                company=record.get("company", ""),
                email=record.get("email", ""),
                phone=record.get("phone", ""),
                table=table,
            )
        )
    if not rows:
        errors.append((0, "The file has no data rows.", ""))
    if errors:
        raise ImportErrors(errors)
    exhibition.participants.all().delete()  # cascades to requests and meetings
    Participant.objects.bulk_create(participants)
    exhibition.last_run = None
    exhibition.save(update_fields=["last_run"])
    return len(participants)


@transaction.atomic
def import_requests(exhibition, file):
    """Replace the exhibition's meeting requests. Removes existing meetings.

    Two layouts are accepted:

    * long – one row per request, with a visitor column and an exhibitor column;
    * wide – one row per visitor, the visitor column followed by that visitor's
      exhibitors, first choice first.

    Priority is the order in which a visitor's requests appear, unless the long
    layout carries an explicit priority column. A request that appears twice is
    kept once. Returns ``(requests_saved, duplicates_skipped)``.
    """
    try:
        rows = _read_rows(file, REQUEST_HEADERS, required=["visitor", "exhibitor"])
        wide = False
    except ImportErrors:
        file.seek(0)
        rows = _read_rows(file, {"visitor": REQUEST_HEADERS["visitor"]}, required=["visitor"])
        wide = True
        if not any(extras for _number, _record, extras in rows):
            raise

    by_code = {normalise(p.code): p for p in exhibition.participants.all()}
    errors, seen, parsed, duplicates = [], set(), [], 0
    for number, record, extras in rows:
        visitor = by_code.get(normalise(record["visitor"]))
        if visitor is None or visitor.kind != Participant.VISITOR:
            errors.append((number, "Visitor is not in the participants list:", record["visitor"]))
            continue
        wanted = extras if wide else [record["exhibitor"]]
        explicit = None
        if not wide and record.get("rank"):
            if not record["rank"].isdigit() or int(record["rank"]) < 1:
                errors.append((number, "Priority must be a positive number:", record["rank"]))
                continue
            explicit = int(record["rank"])
        for exhibitor_code in wanted:
            exhibitor = by_code.get(normalise(exhibitor_code))
            if exhibitor is None or exhibitor.kind != Participant.EXHIBITOR:
                errors.append((number, "Exhibitor is not in the participants list:", exhibitor_code))
                continue
            pair = (visitor.id, exhibitor.id)
            if pair in seen:
                duplicates += 1
                continue
            seen.add(pair)
            parsed.append((explicit if explicit is not None else 10**9, len(parsed), visitor, exhibitor))
    if not parsed and not errors:
        errors.append((0, "The file has no data rows.", ""))
    if errors:
        raise ImportErrors(errors)

    # Rank = position among the visitor's own requests (explicit priority first, then file order).
    per_visitor = {}
    for item in parsed:
        per_visitor.setdefault(item[2].id, []).append(item)
    requests = []
    for items in per_visitor.values():
        for rank, (_explicit, _order, visitor, exhibitor) in enumerate(sorted(items, key=lambda x: x[:2]), 1):
            requests.append(MeetingRequest(exhibition=exhibition, visitor=visitor, exhibitor=exhibitor, rank=rank))

    Meeting.objects.filter(exhibition=exhibition).delete()
    exhibition.requests.all().delete()
    MeetingRequest.objects.bulk_create(requests)
    exhibition.last_run = None
    exhibition.save(update_fields=["last_run"])
    return len(requests), duplicates
