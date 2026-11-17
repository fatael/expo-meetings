"""Create the first administrator from environment variables, if it does not exist yet.

Lets a hosted installation get its first login without anyone typing commands.
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create an administrator from ADMIN_USERNAME / ADMIN_PASSWORD if missing."

    def handle(self, **options):
        username = os.environ.get("ADMIN_USERNAME", "").strip()
        password = os.environ.get("ADMIN_PASSWORD", "")
        if not username or not password:
            self.stdout.write("ADMIN_USERNAME / ADMIN_PASSWORD not set; skipping.")
            return
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Administrator '{username}' already exists.")
            return
        User.objects.create_superuser(username=username, password=password)
        self.stdout.write(f"Administrator '{username}' created.")
