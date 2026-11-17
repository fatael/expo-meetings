"""Turning an exhibition's time ranges into meeting slots."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta


@dataclass(frozen=True)
class Slot:
    date: date
    start: time
    end: time

    @property
    def key(self):
        return f"{self.date.isoformat()} {self.start.strftime('%H:%M')}"

    @property
    def label(self):
        text = f"{self.date.strftime('%d/%m/%Y')} {self.start.strftime('%H:%M')}–{self.end.strftime('%H:%M')}"
        return f"\u2066{text}\u2069"  # stays left-to-right inside Hebrew text


def slots_for_range(day, start, end, minutes):
    """Return (slots, leftover_minutes) for one range."""
    cursor = datetime.combine(day, start)
    stop = datetime.combine(day, end)
    step = timedelta(minutes=minutes)
    slots = []
    while cursor + step <= stop:
        slots.append(Slot(day, cursor.time(), (cursor + step).time()))
        cursor += step
    leftover = int((stop - cursor).total_seconds() // 60) if stop > cursor else 0
    return slots, leftover


def build_slots(exhibition):
    """Return (slots, warnings). Each warning is (range, leftover_minutes)."""
    slots, warnings = [], []
    for r in exhibition.ranges.all():
        made, leftover = slots_for_range(r.date, r.start, r.end, exhibition.meeting_minutes)
        slots.extend(made)
        if leftover:
            warnings.append((r, leftover))
    return slots, warnings


def parse_key(key):
    stamp = datetime.strptime(key, "%Y-%m-%d %H:%M")
    return stamp.date(), stamp.time()
