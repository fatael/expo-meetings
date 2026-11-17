"""Reading and validating the two Excel files the organiser uploads.

Both imports are all-or-nothing: if any row is wrong, nothing is saved and the
organiser gets the full list of problems.
"""
from django.db import transaction
from openpyxl import load_workbook

from .models import Meeting, MeetingRequest, Participant

# Accepted header names (lower-cased) for each field, in English and Hebrew.
PARTICIPANT_HEADERS = {
    "code": ["id", "code", "מזהה", "מספר"],
    "kind": ["type", "kind", "סוג"],
    "name": ["name", "שם"],
    "company": ["company", "חברה"],
    "email": ["email", "e-mail", 'דוא"ל', "דואל", "אימייל", "מייל"],
    "phone": ["phone", "טלפון"],
    "table": ["table", "שולחן"],
}
REQUEST_HEADERS = {
    "visitor": ["visitor_id", "visitor id", "visitor", "מזהה מבקר", "מבקר"],
    "exhibitor": ["exhibitor_id", "exhibitor id", "exhibitor", "מזהה מציג", "מציג"],
    "rank": ["priority", "rank", "עדיפות"],
}
KIND_WORDS = {
    "exhibitor": Participant.EXHIBITOR,
    "מציג": Participant.EXHIBITOR,
    "visitor": Participant.VISITOR,
    "מבקר": Participant.VISITOR,
}


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
    return str(value).strip()


def _read_rows(file, headers, required):
    """Yield (row_number, {field: text}) for every non-empty row."""
    try:
        sheet = load_workbook(file, read_only=True, data_only=True).active
    except Exception as exc:  # not a readable .xlsx file
        raise ImportErrors([(0, "The file could not be read as an Excel (.xlsx) file.", "")]) from exc
    rows = sheet.iter_rows(values_only=True)
    header_row = next(rows, None)
    if header_row is None:
        raise ImportErrors([(0, "The file is empty.", "")])
    names = [_text(cell).lower() for cell in header_row]
    columns = {}
    for field, accepted in headers.items():
        for index, name in enumerate(names):
            if name in accepted:
                columns[field] = index
                break
    missing = [headers[field][0] for field in required if field not in columns]
    if missing:
        raise ImportErrors([(1, "Missing column(s):", ", ".join(missing))])
    result = []
    for number, row in enumerate(rows, start=2):
        record = {f: _text(row[i]) if i < len(row) else "" for f, i in columns.items()}
        if any(record.values()):
            result.append((number, record))
    return result


@transaction.atomic
def import_participants(exhibition, file):
    """Replace the exhibition's participants. Removes existing requests and meetings."""
    rows = _read_rows(file, PARTICIPANT_HEADERS, required=["code", "kind", "name"])
    errors, seen, participants = [], set(), []
    for number, record in rows:
        code, kind_word = record["code"], record["kind"].lower()
        if not code:
            errors.append((number, "Missing ID.", ""))
            continue
        if code in seen:
            errors.append((number, "Duplicate ID:", code))
            continue
        seen.add(code)
        kind = KIND_WORDS.get(kind_word)
        if kind is None:
            errors.append((number, "Type must be exhibitor or visitor:", record["kind"]))
            continue
        if not record["name"]:
            errors.append((number, "Missing name.", ""))
            continue
        table = None
        if record.get("table"):
            if not record["table"].isdigit():
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

    Priority is the order of a visitor's rows, unless a priority column is present.
    """
    rows = _read_rows(file, REQUEST_HEADERS, required=["visitor", "exhibitor"])
    by_code = {p.code: p for p in exhibition.participants.all()}
    errors, seen, parsed = [], set(), []
    for number, record in rows:
        visitor = by_code.get(record["visitor"])
        exhibitor = by_code.get(record["exhibitor"])
        if visitor is None or visitor.kind != Participant.VISITOR:
            errors.append((number, "Visitor is not in the participants list:", record["visitor"]))
            continue
        if exhibitor is None or exhibitor.kind != Participant.EXHIBITOR:
            errors.append((number, "Exhibitor is not in the participants list:", record["exhibitor"]))
            continue
        pair = (visitor.id, exhibitor.id)
        if pair in seen:
            errors.append((number, "Duplicate request:", f"{visitor.code} → {exhibitor.code}"))
            continue
        seen.add(pair)
        explicit = None
        if record.get("rank"):
            if not record["rank"].isdigit() or int(record["rank"]) < 1:
                errors.append((number, "Priority must be a positive number:", record["rank"]))
                continue
            explicit = int(record["rank"])
        parsed.append((number, visitor, exhibitor, explicit))
    if not rows:
        errors.append((0, "The file has no data rows.", ""))
    if errors:
        raise ImportErrors(errors)

    # Rank = position among the visitor's own requests (explicit priority first, then row order).
    per_visitor = {}
    for number, visitor, exhibitor, explicit in parsed:
        per_visitor.setdefault(visitor.id, []).append((explicit if explicit is not None else 10**9, number, visitor, exhibitor))
    requests = []
    for items in per_visitor.values():
        for rank, (_explicit, _number, visitor, exhibitor) in enumerate(sorted(items, key=lambda x: x[:2]), start=1):
            requests.append(MeetingRequest(exhibition=exhibition, visitor=visitor, exhibitor=exhibitor, rank=rank))

    Meeting.objects.filter(exhibition=exhibition).delete()
    exhibition.requests.all().delete()
    MeetingRequest.objects.bulk_create(requests)
    exhibition.last_run = None
    exhibition.save(update_fields=["last_run"])
    return len(requests)
