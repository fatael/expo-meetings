"""Output files: the Excel workbook, the personal-schedule PDFs and the upload templates."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from io import BytesIO

from django.template.loader import render_to_string
from openpyxl import Workbook
from openpyxl.styles import Font

from .i18n import tr
from .models import Participant
from .services import unmet_requests


def _end_time(meeting, minutes):
    return (datetime.combine(meeting.date, meeting.start) + timedelta(minutes=minutes)).time()


def _sheet(workbook, title, headers, lang, first=False):
    sheet = workbook.active if first else workbook.create_sheet()
    sheet.title = tr(lang, title)
    sheet.sheet_view.rightToLeft = lang == "he"
    sheet.append([tr(lang, h) for h in headers])
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    sheet.freeze_panes = "A2"
    return sheet


def _autosize(sheet):
    for column in sheet.columns:
        width = max((len(str(cell.value)) for cell in column if cell.value is not None), default=8)
        sheet.column_dimensions[column[0].column_letter].width = min(max(width + 2, 10), 45)


def excel_workbook(exhibition, lang):
    """Three sheets: every meeting, the requests that were not granted, and load per participant."""
    workbook = Workbook()
    meetings = list(exhibition.meetings.select_related("visitor", "exhibitor", "exhibition"))

    sheet = _sheet(
        workbook,
        "Meetings",
        ["Date", "Start", "End time", "Table", "Visitor ID", "Visitor name", "Visitor company",
         "Exhibitor ID", "Exhibitor name", "Exhibitor company", "Manual"],
        lang,
        first=True,
    )
    for m in meetings:
        sheet.append([
            m.date.strftime("%d/%m/%Y"), m.start.strftime("%H:%M"),
            _end_time(m, exhibition.meeting_minutes).strftime("%H:%M"), m.table,
            m.visitor.code, m.visitor.name, m.visitor.company,
            m.exhibitor.code, m.exhibitor.name, m.exhibitor.company,
            tr(lang, "Yes") if m.manual else "",
        ])
    _autosize(sheet)

    sheet = _sheet(
        workbook,
        "Unmet requests",
        ["Visitor ID", "Visitor name", "Visitor company", "Exhibitor ID", "Exhibitor name",
         "Exhibitor company", "Priority"],
        lang,
    )
    for r in unmet_requests(exhibition):
        sheet.append([r.visitor.code, r.visitor.name, r.visitor.company,
                      r.exhibitor.code, r.exhibitor.name, r.exhibitor.company, r.rank])
    _autosize(sheet)

    requested = Counter()
    for visitor_id, exhibitor_id in exhibition.requests.values_list("visitor_id", "exhibitor_id"):
        requested[visitor_id] += 1
        requested[exhibitor_id] += 1
    scheduled = Counter()
    for m in meetings:
        scheduled[m.visitor_id] += 1
        scheduled[m.exhibitor_id] += 1
    sheet = _sheet(workbook, "Load", ["ID", "Type", "Name", "Company", "Table", "Requested", "Scheduled"], lang)
    for p in exhibition.participants.all():
        sheet.append([p.code, tr(lang, p.kind), p.name, p.company, p.table,
                      requested.get(p.id, 0), scheduled.get(p.id, 0)])
    _autosize(sheet)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


PDF_CHUNK = 40  # participants rendered at a time, to keep memory use low


def _schedule_pages(exhibition, kind):
    meetings_of = defaultdict(list)
    for m in exhibition.meetings.select_related("visitor", "exhibitor", "exhibition"):
        owner, other = (m.visitor, m.exhibitor) if kind == Participant.VISITOR else (m.exhibitor, m.visitor)
        meetings_of[owner.id].append({
            "date": m.date,
            "start": m.start,
            "end": _end_time(m, exhibition.meeting_minutes),
            "table": m.table,
            "other": other,
        })
    return [
        {"participant": p, "meetings": meetings_of.get(p.id, [])}
        for p in exhibition.participants.filter(kind=kind)
    ]


def personal_schedules_html(exhibition, kind, lang, pages=None):
    """One page per participant of the given kind, as a single HTML document."""
    return render_to_string(
        "meetings/personal_schedules.html",
        {
            "exhibition": exhibition,
            "pages": _schedule_pages(exhibition, kind) if pages is None else pages,
            "lang": lang,
            "direction": "rtl" if lang == "he" else "ltr",
            "seated": kind == exhibition.seated_kind,
        },
    )


def personal_schedules_pdf(exhibition, kind, lang):
    # Imported here: these are slow to load and only needed for PDFs.
    from pypdf import PdfWriter
    from weasyprint import HTML

    pages = _schedule_pages(exhibition, kind)
    writer = PdfWriter()
    for start in range(0, max(len(pages), 1), PDF_CHUNK):
        html = personal_schedules_html(exhibition, kind, lang, pages[start:start + PDF_CHUNK])
        writer.append(BytesIO(HTML(string=html).write_pdf()))
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def template_workbook(what, lang):
    """An example file showing the expected columns."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.sheet_view.rightToLeft = lang == "he"
    if what == "participants":
        if lang == "he":
            sheet.append(["מזהה", "סוג", "שם", "חברה", 'דוא"ל', "טלפון", "שולחן"])
            sheet.append(["E001", "מציג", "דנה לוי", "מלונות הים", "dana@example.com", "050-0000000", ""])
            sheet.append(["V001", "מבקר", "John Smith", "Smith Travel", "john@example.com", "", ""])
        else:
            sheet.append(["id", "type", "name", "company", "email", "phone", "table"])
            sheet.append(["E001", "exhibitor", "Dana Levi", "Sea Hotels", "dana@example.com", "050-0000000", ""])
            sheet.append(["V001", "visitor", "John Smith", "Smith Travel", "john@example.com", "", ""])
    else:
        if lang == "he":
            sheet.append(["מזהה מבקר", "מזהה מציג"])
        else:
            sheet.append(["visitor_id", "exhibitor_id"])
        sheet.append(["V001", "E001"])
        sheet.append(["V001", "E002"])
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    _autosize(sheet)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
