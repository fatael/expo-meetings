"""Operations on an exhibition: running the scheduler, statistics, manual edits."""
from collections import Counter

from django.conf import settings
from django.db import transaction

from . import scheduler
from .models import Meeting, MeetingRequest, Participant
from .slots import build_slots


class ScheduleError(Exception):
    """A user-facing problem. ``args[0]`` is a translation key."""


def assign_tables(exhibition):
    """Give the seated side table numbers, keeping any that came from the Excel file."""
    seated = list(exhibition.participants.filter(kind=exhibition.seated_kind).order_by("code"))
    taken = {p.table for p in seated if p.table}
    number = 1
    changed = []
    for participant in seated:
        if participant.table:
            continue
        while number in taken:
            number += 1
        participant.table = number
        taken.add(number)
        changed.append(participant)
    Participant.objects.bulk_update(changed, ["table"])


def overview(exhibition):
    """Supply and demand figures shown before a run."""
    slots, warnings = build_slots(exhibition)
    kinds = Counter(exhibition.participants.values_list("kind", flat=True))
    n_exhibitors, n_visitors = kinds[Participant.EXHIBITOR], kinds[Participant.VISITOR]
    n_requests = exhibition.requests.count()
    demand = Counter(exhibition.requests.values_list("exhibitor_id", flat=True))
    return {
        "slots": slots,
        "slot_warnings": warnings,
        "n_slots": len(slots),
        "n_exhibitors": n_exhibitors,
        "n_visitors": n_visitors,
        "n_requests": n_requests,
        "supply": n_exhibitors * len(slots),
        "oversubscribed": sum(1 for count in demand.values() if count > len(slots)),
        "suggested_cap": scheduler.suggested_cap(n_requests, n_visitors, n_exhibitors, len(slots)),
    }


def result_stats(exhibition):
    """Figures describing the current timetable."""
    meetings = list(exhibition.meetings.values_list("visitor_id", "exhibitor_id"))
    n_requests = exhibition.requests.count()
    requested_pairs = set(exhibition.requests.values_list("visitor_id", "exhibitor_id"))
    granted = sum(1 for pair in meetings if pair in requested_pairs)
    per_visitor = Counter(v for v, _e in meetings)
    per_exhibitor = Counter(e for _v, e in meetings)
    visitors_with_requests = set(exhibition.requests.values_list("visitor_id", flat=True))
    exhibitors = list(exhibition.participants.filter(kind=Participant.EXHIBITOR).values_list("id", flat=True))

    def spread(ids, counts):
        values = [counts.get(i, 0) for i in ids]
        if not values:
            return {"min": 0, "avg": 0, "max": 0}
        return {"min": min(values), "avg": round(sum(values) / len(values), 1), "max": max(values)}

    return {
        "meetings": len(meetings),
        "requests": n_requests,
        "granted": granted,
        "unmet": n_requests - granted,
        "granted_pct": round(100 * granted / n_requests, 1) if n_requests else 0,
        "visitors": spread(visitors_with_requests, per_visitor),
        "exhibitors": spread(exhibitors, per_exhibitor),
        "visitors_without_meeting": sum(1 for v in visitors_with_requests if not per_visitor.get(v)),
    }


@transaction.atomic
def run_schedule(exhibition):
    """Build the timetable from scratch. Replaces every existing meeting."""
    if exhibition.locked:
        raise ScheduleError("The timetable is locked. Unlock it before running again.")
    slots, _warnings = build_slots(exhibition)
    if not slots:
        raise ScheduleError("Define at least one time range before running.")
    requests = list(exhibition.requests.values_list("id", "visitor_id", "exhibitor_id", "rank"))
    if not requests:
        raise ScheduleError("Upload the requests file before running.")

    plan = scheduler.schedule(
        [(visitor, exhibitor, rank) for _id, visitor, exhibitor, rank in requests],
        len(slots),
        exhibition.max_per_visitor,
        settings.SCHEDULER_TIME_LIMIT,
        settings.SCHEDULER_WORKERS,
    )
    exhibition.meetings.all().delete()
    Meeting.objects.bulk_create(
        Meeting(
            exhibition=exhibition,
            visitor_id=requests[index][1],
            exhibitor_id=requests[index][2],
            date=slots[slot].date,
            start=slots[slot].start,
        )
        for index, slot in plan.items()
    )
    assign_tables(exhibition)
    exhibition.last_run = result_stats(exhibition)
    exhibition.save(update_fields=["last_run"])
    return exhibition.last_run


def check_free(exhibition, visitor, exhibitor, date, start, ignore=None):
    """Raise ScheduleError if a meeting at that time would clash with an existing one."""
    others = exhibition.meetings.all()
    if ignore is not None:
        others = others.exclude(pk=ignore.pk)
    if visitor.kind != Participant.VISITOR or exhibitor.kind != Participant.EXHIBITOR:
        raise ScheduleError("A meeting needs one visitor and one exhibitor.")
    if others.filter(visitor=visitor, exhibitor=exhibitor).exists():
        raise ScheduleError("These two already have a meeting.")
    if others.filter(visitor=visitor, date=date, start=start).exists():
        raise ScheduleError("The visitor already has a meeting at that time.")
    if others.filter(exhibitor=exhibitor, date=date, start=start).exists():
        raise ScheduleError("The exhibitor already has a meeting at that time.")


def refresh_stats(exhibition):
    exhibition.last_run = result_stats(exhibition)
    exhibition.save(update_fields=["last_run"])


def unmet_requests(exhibition):
    met = set(exhibition.meetings.values_list("visitor_id", "exhibitor_id"))
    return [
        request
        for request in MeetingRequest.objects.filter(exhibition=exhibition).select_related("visitor", "exhibitor")
        if (request.visitor_id, request.exhibitor_id) not in met
    ]
