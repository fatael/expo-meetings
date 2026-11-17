"""Create two sample Excel files (participants and requests) for trying the system out."""
import random
from pathlib import Path

from django.core.management.base import BaseCommand
from openpyxl import Workbook


class Command(BaseCommand):
    help = "Write sample participants.xlsx and requests.xlsx into a folder."

    def add_arguments(self, parser):
        parser.add_argument("folder", nargs="?", default="sample")
        parser.add_argument("--exhibitors", type=int, default=300)
        parser.add_argument("--visitors", type=int, default=400)
        parser.add_argument("--seed", type=int, default=1)

    def handle(self, folder, exhibitors, visitors, seed, **options):
        random.seed(seed)
        target = Path(folder)
        target.mkdir(parents=True, exist_ok=True)

        book = Workbook()
        sheet = book.active
        sheet.append(["מזהה", "סוג", "שם", "חברה", 'דוא"ל', "טלפון"])
        for i in range(1, exhibitors + 1):
            sheet.append([f"E{i:03d}", "מציג", f"נציג {i}", f"חברה מציגה {i}", f"e{i}@example.com", ""])
        for i in range(1, visitors + 1):
            sheet.append([f"V{i:03d}", "מבקר", f"Visitor {i}", f"Travel Agency {i}", f"v{i}@example.com", ""])
        book.save(target / "participants.xlsx")

        # A few exhibitors are far more popular than the rest, as in a real show.
        weights = [1 / (i + 1) ** 0.8 for i in range(exhibitors)]
        book = Workbook()
        sheet = book.active
        sheet.append(["מזהה מבקר", "מזהה מציג"])
        for v in range(1, visitors + 1):
            wanted = []
            while len(wanted) < min(random.randint(6, 14), exhibitors):
                pick = random.choices(range(1, exhibitors + 1), weights)[0]
                if pick not in wanted:
                    wanted.append(pick)
            for e in wanted:
                sheet.append([f"V{v:03d}", f"E{e:03d}"])
        book.save(target / "requests.xlsx")
        self.stdout.write(f"Wrote {target / 'participants.xlsx'} and {target / 'requests.xlsx'}")
