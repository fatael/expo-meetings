from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import exports, services
from .forms import ExhibitionForm, RangeFormSet
from .i18n import get_language, tr
from .importer import ImportErrors, import_participants, import_requests
from .models import Exhibition, Meeting, Participant
from .slots import build_slots, parse_key

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _say(request, level, text, prefix=""):
    messages.add_message(request, level, f"{prefix}{tr(get_language(request), text)}")


def _download(content, content_type, filename):
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def set_language(request, lang):
    if lang in ("he", "en"):
        request.session["lang"] = lang
    back = request.META.get("HTTP_REFERER", "")
    if not url_has_allowed_host_and_scheme(back, allowed_hosts={request.get_host()}):
        back = "exhibition_list"
    return redirect(back)


@login_required
def exhibition_list(request):
    return render(request, "meetings/exhibition_list.html", {"exhibitions": Exhibition.objects.all()})


@login_required
def exhibition_edit(request, pk=None):
    exhibition = get_object_or_404(Exhibition, pk=pk) if pk else None
    if exhibition and exhibition.locked:
        _say(request, messages.ERROR, "The timetable is locked. Unlock it before changing settings.")
        return redirect("exhibition_detail", pk=pk)
    form = ExhibitionForm(request.POST or None, instance=exhibition)
    ranges = RangeFormSet(request.POST or None, instance=exhibition or Exhibition())
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            saved = form.save()
            ranges = RangeFormSet(request.POST, instance=saved)
            if ranges.is_valid():
                ranges.save()
                services.assign_tables(saved)  # the seated side may have changed
                _say(request, messages.SUCCESS, "Settings saved.")
                if saved.meetings.exists():
                    _say(request, messages.WARNING,
                         "Changing the settings does not change existing meetings. "
                         "Run the scheduling again to apply them.")
                return redirect("exhibition_detail", pk=saved.pk)
            transaction.set_rollback(True)
    return render(request, "meetings/exhibition_form.html",
                  {"form": form, "ranges": ranges, "exhibition": exhibition})


@login_required
def exhibition_detail(request, pk):
    exhibition = get_object_or_404(Exhibition, pk=pk)
    context = {"exhibition": exhibition, "overview": services.overview(exhibition),
               "import_errors": request.session.pop("import_errors", None)}
    return render(request, "meetings/exhibition_detail.html", context)


@login_required
@require_POST
def upload(request, pk, what):
    exhibition = get_object_or_404(Exhibition, pk=pk)
    if what not in ("participants", "requests"):
        raise Http404
    if exhibition.locked:
        _say(request, messages.ERROR, "The timetable is locked. Unlock it before uploading files.")
        return redirect("exhibition_detail", pk=pk)
    file = request.FILES.get("file")
    if not file:
        _say(request, messages.ERROR, "Choose a file.")
        return redirect("exhibition_detail", pk=pk)
    try:
        if what == "participants":
            count = import_participants(exhibition, file)
            _say(request, messages.SUCCESS, "participants imported.", prefix=f"{count} ")
        else:
            count, duplicates = import_requests(exhibition, file)
            _say(request, messages.SUCCESS, "requests imported.", prefix=f"{count} ")
            if duplicates:
                _say(request, messages.WARNING, "repeated requests were ignored.", prefix=f"{duplicates} ")
    except ImportErrors as problem:
        lang = get_language(request)
        request.session["import_errors"] = [
            {"row": row, "text": f"{tr(lang, text)} {detail}".strip()} for row, text, detail in problem.errors[:200]
        ]
    return redirect("exhibition_detail", pk=pk)


@login_required
def template_file(request, pk, what):
    if what not in ("participants", "requests"):
        raise Http404
    return _download(exports.template_workbook(what, get_language(request)), XLSX, f"{what}-template.xlsx")


@login_required
@require_POST
def run(request, pk):
    exhibition = get_object_or_404(Exhibition, pk=pk)
    try:
        services.run_schedule(exhibition)
        _say(request, messages.SUCCESS, "Scheduling finished.")
    except (services.ScheduleError, RuntimeError) as problem:
        _say(request, messages.ERROR, str(problem))
    return redirect("exhibition_detail", pk=pk)


@login_required
@require_POST
def toggle_lock(request, pk):
    exhibition = get_object_or_404(Exhibition, pk=pk)
    exhibition.locked = not exhibition.locked
    exhibition.save(update_fields=["locked"])
    _say(request, messages.SUCCESS,
         "The timetable is locked." if exhibition.locked else "The timetable is unlocked.")
    return redirect("exhibition_detail", pk=pk)


@login_required
def timetable(request, pk):
    exhibition = get_object_or_404(Exhibition, pk=pk)
    participants = list(exhibition.participants.all())
    meetings = exhibition.meetings.select_related("visitor", "exhibitor", "exhibition")
    selected = request.GET.get("participant", "")
    if selected.isdigit():
        meetings = meetings.filter(visitor_id=selected) | meetings.filter(exhibitor_id=selected)
    total = meetings.count()
    slots, _warnings = build_slots(exhibition)
    return render(request, "meetings/timetable.html", {
        "exhibition": exhibition,
        "meetings": meetings[:500],
        "truncated": total > 500,
        "selected": selected,
        "visitors": [p for p in participants if p.kind == Participant.VISITOR],
        "exhibitors": [p for p in participants if p.kind == Participant.EXHIBITOR],
        "slots": slots,
    })


def _editable(request, pk):
    exhibition = get_object_or_404(Exhibition, pk=pk)
    if exhibition.locked:
        _say(request, messages.ERROR, "The timetable is locked. Unlock it before editing.")
        return exhibition, False
    return exhibition, True


def _slot_from_post(request, exhibition):
    slots, _warnings = build_slots(exhibition)
    key = request.POST.get("slot", "")
    if key not in {slot.key for slot in slots}:
        raise Http404
    return parse_key(key)


@login_required
@require_POST
def meeting_add(request, pk):
    exhibition, ok = _editable(request, pk)
    if ok:
        visitor = get_object_or_404(Participant, pk=request.POST.get("visitor"), exhibition=exhibition)
        exhibitor = get_object_or_404(Participant, pk=request.POST.get("exhibitor"), exhibition=exhibition)
        date, start = _slot_from_post(request, exhibition)
        try:
            services.check_free(exhibition, visitor, exhibitor, date, start)
            Meeting.objects.create(exhibition=exhibition, visitor=visitor, exhibitor=exhibitor,
                                   date=date, start=start, manual=True)
            services.assign_tables(exhibition)
            services.refresh_stats(exhibition)
            _say(request, messages.SUCCESS, "Meeting added.")
        except services.ScheduleError as problem:
            _say(request, messages.ERROR, str(problem))
    return redirect("timetable", pk=pk)


@login_required
def meeting_move(request, pk, meeting_id):
    exhibition = get_object_or_404(Exhibition, pk=pk)
    meeting = get_object_or_404(Meeting, pk=meeting_id, exhibition=exhibition)
    if request.method == "POST":
        exhibition, ok = _editable(request, pk)
        if ok:
            date, start = _slot_from_post(request, exhibition)
            try:
                services.check_free(exhibition, meeting.visitor, meeting.exhibitor, date, start, ignore=meeting)
                meeting.date, meeting.start, meeting.manual = date, start, True
                meeting.save()
                _say(request, messages.SUCCESS, "Meeting moved.")
                return redirect("timetable", pk=pk)
            except services.ScheduleError as problem:
                _say(request, messages.ERROR, str(problem))
        else:
            return redirect("timetable", pk=pk)
    slots, _warnings = build_slots(exhibition)
    current = f"{meeting.date.isoformat()} {meeting.start.strftime('%H:%M')}"
    return render(request, "meetings/meeting_move.html",
                  {"exhibition": exhibition, "meeting": meeting, "slots": slots, "current": current})


@login_required
@require_POST
def meeting_delete(request, pk, meeting_id):
    exhibition, ok = _editable(request, pk)
    if ok:
        get_object_or_404(Meeting, pk=meeting_id, exhibition=exhibition).delete()
        services.refresh_stats(exhibition)
        _say(request, messages.SUCCESS, "Meeting deleted.")
    return redirect("timetable", pk=pk)


@login_required
def export_excel(request, pk):
    exhibition = get_object_or_404(Exhibition, pk=pk)
    return _download(exports.excel_workbook(exhibition, get_language(request)), XLSX, f"timetable-{pk}.xlsx")


@login_required
def export_pdf(request, pk, kind):
    exhibition = get_object_or_404(Exhibition, pk=pk)
    if kind not in (Participant.VISITOR, Participant.EXHIBITOR):
        raise Http404
    content = exports.personal_schedules_pdf(exhibition, kind, get_language(request))
    return _download(content, "application/pdf", f"schedules-{kind}s-{pk}.pdf")


@login_required
def participants(request, pk):
    exhibition = get_object_or_404(Exhibition, pk=pk)
    rows = services.participant_rows(exhibition)
    return render(request, "meetings/participants.html", {
        "exhibition": exhibition,
        "exhibitors": [r for r in rows if r["participant"].kind == Participant.EXHIBITOR],
        "visitors": [r for r in rows if r["participant"].kind == Participant.VISITOR],
    })


@login_required
@require_POST
def exhibition_delete(request, pk):
    exhibition = get_object_or_404(Exhibition, pk=pk)
    if exhibition.locked:
        _say(request, messages.ERROR, "The timetable is locked. Unlock it before deleting the exhibition.")
        return redirect("exhibition_detail", pk=pk)
    exhibition.delete()
    _say(request, messages.SUCCESS, "The exhibition was deleted.")
    return redirect("exhibition_list")


def not_found(request, exception=None):
    return render(request, "meetings/404.html", status=404)
