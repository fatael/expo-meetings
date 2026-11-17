from django.db import models


class Exhibition(models.Model):
    EXHIBITORS_SEATED = "exhibitors"
    VISITORS_SEATED = "visitors"
    SEATING_CHOICES = [
        (EXHIBITORS_SEATED, "Exhibitors seated, visitors move"),
        (VISITORS_SEATED, "Visitors seated, exhibitors move"),
    ]
    MINUTES_CHOICES = [(10, "10"), (15, "15"), (20, "20")]

    name = models.CharField(max_length=200)
    meeting_minutes = models.PositiveSmallIntegerField(choices=MINUTES_CHOICES, default=15)
    seating = models.CharField(max_length=20, choices=SEATING_CHOICES, default=EXHIBITORS_SEATED)
    max_per_visitor = models.PositiveSmallIntegerField(null=True, blank=True)
    locked = models.BooleanField(default=False)
    last_run = models.JSONField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.name

    @property
    def seated_kind(self):
        return Participant.EXHIBITOR if self.seating == self.EXHIBITORS_SEATED else Participant.VISITOR


class TimeRange(models.Model):
    """A continuous block of meeting time. A break is simply the gap between two ranges."""

    exhibition = models.ForeignKey(Exhibition, on_delete=models.CASCADE, related_name="ranges")
    date = models.DateField()
    start = models.TimeField()
    end = models.TimeField()

    class Meta:
        ordering = ["date", "start"]


class Participant(models.Model):
    EXHIBITOR = "exhibitor"
    VISITOR = "visitor"
    KIND_CHOICES = [(EXHIBITOR, "Exhibitor"), (VISITOR, "Visitor")]

    exhibition = models.ForeignKey(Exhibition, on_delete=models.CASCADE, related_name="participants")
    code = models.CharField(max_length=50)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    name = models.CharField(max_length=200)
    company = models.CharField(max_length=200, blank=True)
    email = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    table = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["kind", "code"]
        constraints = [
            models.UniqueConstraint(fields=["exhibition", "code"], name="unique_code_per_exhibition")
        ]

    def __str__(self):
        return f"{self.code} – {self.name}"

    @property
    def label(self):
        return f"{self.name} ({self.company})" if self.company else self.name


class MeetingRequest(models.Model):
    exhibition = models.ForeignKey(Exhibition, on_delete=models.CASCADE, related_name="requests")
    visitor = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="requests_made")
    exhibitor = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="requests_received")
    rank = models.PositiveIntegerField(help_text="1 = the visitor's first priority")

    class Meta:
        ordering = ["visitor__code", "rank"]
        constraints = [
            models.UniqueConstraint(fields=["visitor", "exhibitor"], name="unique_request_pair")
        ]


class Meeting(models.Model):
    exhibition = models.ForeignKey(Exhibition, on_delete=models.CASCADE, related_name="meetings")
    visitor = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="meetings_as_visitor")
    exhibitor = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="meetings_as_exhibitor")
    date = models.DateField()
    start = models.TimeField()
    manual = models.BooleanField(default=False)

    class Meta:
        ordering = ["date", "start", "exhibitor__code"]
        constraints = [
            models.UniqueConstraint(fields=["visitor", "date", "start"], name="visitor_one_meeting_per_slot"),
            models.UniqueConstraint(fields=["exhibitor", "date", "start"], name="exhibitor_one_meeting_per_slot"),
            models.UniqueConstraint(fields=["visitor", "exhibitor"], name="one_meeting_per_pair"),
        ]

    @property
    def table(self):
        seated = self.exhibitor if self.exhibition.seating == Exhibition.EXHIBITORS_SEATED else self.visitor
        return seated.table
