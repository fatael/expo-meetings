from django.contrib import admin

from .models import Exhibition, Meeting, MeetingRequest, Participant, TimeRange

admin.site.register([Exhibition, TimeRange, Participant, MeetingRequest, Meeting])
