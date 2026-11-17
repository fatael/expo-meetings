import random
from collections import Counter
from datetime import date, time
from io import BytesIO

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from openpyxl import Workbook, load_workbook

from meetings import scheduler, services
from meetings.importer import ImportErrors, import_participants, import_requests
from meetings.models import Exhibition, Meeting, Participant, TimeRange
from meetings.slots import slots_for_range


def xlsx(rows):
    book = Workbook()
    for row in rows:
        book.active.append(row)
    buffer = BytesIO()
    book.save(buffer)
    buffer.seek(0)
    return buffer


class SlotTests(SimpleTestCase):
    def test_user_example(self):
        day = date(2026, 12, 1)
        for minutes, expected in [(10, 12 + 9), (15, 8 + 6), (20, 6 + 4)]:
            a, _ = slots_for_range(day, time(11), time(13), minutes)
            b, _ = slots_for_range(day, time(13, 30), time(15), minutes)
            self.assertEqual(len(a) + len(b), expected)

    def test_leftover_minutes(self):
        slots, leftover = slots_for_range(date(2026, 12, 1), time(13, 30), time(15), 20)
        self.assertEqual((len(slots), leftover), (4, 10))


class SchedulerTests(SimpleTestCase):
    def assert_valid(self, requests, plan, n_slots, cap=None):
        self.assertEqual(len({(requests[i][0], s) for i, s in plan.items()}), len(plan))
        self.assertEqual(len({(requests[i][1], s) for i, s in plan.items()}), len(plan))
        self.assertTrue(all(0 <= s < n_slots for s in plan.values()))
        if cap is not None:
            self.assertLessEqual(max(Counter(requests[i][0] for i in plan).values()), cap)

    def test_everything_granted_when_supply_is_enough(self):
        requests = [(v, e, e + 1) for v in range(4) for e in range(4)]
        plan = scheduler.schedule(requests, 4)
        self.assertEqual(len(plan), 16)
        self.assert_valid(requests, plan, 4)

    def test_scarce_exhibitor_is_shared_fairly(self):
        # Ten visitors all want exhibitor 0 first and exhibitor 1 second; two slots only.
        requests = [(v, e, e + 1) for v in range(10) for e in range(2)]
        plan = scheduler.schedule(requests, 2)
        self.assertEqual(len(plan), 4)
        per_visitor = Counter(requests[i][0] for i in plan)
        self.assertEqual(max(per_visitor.values()), 1)  # nobody gets two while others get none
        self.assert_valid(requests, plan, 2)

    def test_higher_priority_preferred(self):
        # One slot: the visitor can have only one meeting, and it should be the first priority.
        plan = scheduler.schedule([("v", "a", 2), ("v", "b", 1)], 1)
        self.assertEqual(list(plan), [1])

    def test_cap_per_visitor(self):
        requests = [(0, e, e + 1) for e in range(8)]
        plan = scheduler.schedule(requests, 8, max_per_visitor=3)
        self.assertEqual(sorted(requests[i][2] for i in plan), [1, 2, 3])

    def test_full_size_run(self):
        random.seed(7)
        weights = [1 / (i + 1) ** 0.8 for i in range(300)]
        requests = []
        for v in range(400):
            wanted = []
            while len(wanted) < 10:
                e = random.choices(range(300), weights)[0]
                if e not in wanted:
                    wanted.append(e)
            requests += [(v, e, rank) for rank, e in enumerate(wanted, 1)]
        plan = scheduler.schedule(requests, 16)
        self.assert_valid(requests, plan, 16)
        self.assertLessEqual(max(Counter(requests[i][1] for i in plan).values()), 16)
        self.assertGreater(len(plan), 2000)

    def test_slot_assignment_on_dense_graph(self):
        pairs = [(v, e) for v in range(12) for e in range(12)]
        random.Random(3).shuffle(pairs)
        slot_of = scheduler.assign_slots(pairs, 12)
        self.assertEqual(len(slot_of), 144)
        self.assertEqual(len({(v, s) for (v, _e), s in slot_of.items()}), 144)
        self.assertEqual(len({(e, s) for (_v, e), s in slot_of.items()}), 144)


class ImportAndRunTests(TestCase):
    def setUp(self):
        self.exhibition = Exhibition.objects.create(name="Test", meeting_minutes=20)
        TimeRange.objects.create(exhibition=self.exhibition, date=date(2026, 12, 1), start=time(11), end=time(12))
        self.participants = [
            ["מזהה", "סוג", "שם", "חברה"],
            ["E1", "מציג", "Dana", "Hotels"],
            ["E2", "exhibitor", "Avi", "Tours"],
            ["V1", "מבקר", "John", "Agency"],
            ["V2", "visitor", "Mary", "Agency 2"],
        ]

    def test_import_and_schedule(self):
        self.assertEqual(import_participants(self.exhibition, xlsx(self.participants)), 4)
        requests = [["מזהה מבקר", "מזהה מציג"], ["V1", "E2"], ["V1", "E1"], ["V2", "E2"]]
        self.assertEqual(import_requests(self.exhibition, xlsx(requests)), 3)
        first = self.exhibition.requests.get(visitor__code="V1", exhibitor__code="E2")
        self.assertEqual(first.rank, 1)  # row order is the priority
        stats = services.run_schedule(self.exhibition)
        self.assertEqual(stats["granted"], 3)
        self.assertEqual(stats["unmet"], 0)
        tables = set(Participant.objects.filter(kind="exhibitor").values_list("table", flat=True))
        self.assertEqual(tables, {1, 2})

    def test_bad_rows_are_reported_and_nothing_is_saved(self):
        import_participants(self.exhibition, xlsx(self.participants))
        bad = [["visitor_id", "exhibitor_id"], ["V1", "E9"], ["E1", "E2"], ["V1", "E1"], ["V1", "E1"]]
        with self.assertRaises(ImportErrors) as caught:
            import_requests(self.exhibition, xlsx(bad))
        self.assertEqual([row for row, _text, _detail in caught.exception.errors], [2, 3, 5])
        self.assertEqual(self.exhibition.requests.count(), 0)

    def test_missing_column(self):
        with self.assertRaises(ImportErrors):
            import_participants(self.exhibition, xlsx([["מזהה", "שם"], ["E1", "Dana"]]))

    def test_manual_edit_conflicts(self):
        import_participants(self.exhibition, xlsx(self.participants))
        p = {x.code: x for x in self.exhibition.participants.all()}
        Meeting.objects.create(exhibition=self.exhibition, visitor=p["V1"], exhibitor=p["E1"],
                               date=date(2026, 12, 1), start=time(11))
        with self.assertRaises(services.ScheduleError):
            services.check_free(self.exhibition, p["V1"], p["E2"], date(2026, 12, 1), time(11))
        with self.assertRaises(services.ScheduleError):
            services.check_free(self.exhibition, p["V2"], p["E1"], date(2026, 12, 1), time(11))
        services.check_free(self.exhibition, p["V2"], p["E2"], date(2026, 12, 1), time(11))

    def test_locked_exhibition_cannot_be_rerun(self):
        self.exhibition.locked = True
        self.exhibition.save()
        with self.assertRaises(services.ScheduleError):
            services.run_schedule(self.exhibition)


class PageTests(TestCase):
    def setUp(self):
        User.objects.create_user("organiser", password="secret-pass-1")
        self.client.login(username="organiser", password="secret-pass-1")

    def test_login_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("exhibition_list")).status_code, 302)

    def test_full_flow_through_the_pages(self):
        response = self.client.post(reverse("exhibition_create"), {
            "name": "Expo", "meeting_minutes": 15, "seating": "visitors", "max_per_visitor": "",
            "ranges-TOTAL_FORMS": 2, "ranges-INITIAL_FORMS": 0, "ranges-MIN_NUM_FORMS": 0, "ranges-MAX_NUM_FORMS": 1000,
            "ranges-0-date": "2026-12-01", "ranges-0-start": "11:00", "ranges-0-end": "13:00",
            "ranges-1-date": "2026-12-01", "ranges-1-start": "13:30", "ranges-1-end": "15:00",
        })
        exhibition = Exhibition.objects.get()
        self.assertRedirects(response, reverse("exhibition_detail", args=[exhibition.pk]))
        participants = [["id", "type", "name"]] + [[f"E{i}", "exhibitor", f"Ex {i}"] for i in range(5)] \
            + [[f"V{i}", "visitor", f"Vis {i}"] for i in range(8)]
        requests = [["visitor_id", "exhibitor_id"]] + [[f"V{v}", f"E{e}"] for v in range(8) for e in range(5)]
        for what, rows in (("participants", participants), ("requests", requests)):
            file = xlsx(rows)
            file.name = f"{what}.xlsx"
            self.client.post(reverse("upload", args=[exhibition.pk, what]), {"file": file})
        self.client.post(reverse("run", args=[exhibition.pk]))
        self.assertEqual(exhibition.meetings.count(), 40)
        # Visitors are seated in this exhibition, so they get the tables.
        self.assertTrue(all(p.table for p in exhibition.participants.filter(kind="visitor")))
        for name in ("exhibition_detail", "timetable"):
            self.assertEqual(self.client.get(reverse(name, args=[exhibition.pk])).status_code, 200)
        book = load_workbook(BytesIO(self.client.get(reverse("export_excel", args=[exhibition.pk])).content))
        self.assertEqual(book.worksheets[0].max_row, 41)
        pdf = self.client.get(reverse("export_pdf", args=[exhibition.pk, "visitor"]))
        self.assertTrue(pdf.content.startswith(b"%PDF"))
