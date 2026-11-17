from django import forms
from django.forms import inlineformset_factory

from .models import Exhibition, TimeRange


class ExhibitionForm(forms.ModelForm):
    class Meta:
        model = Exhibition
        fields = ["name", "meeting_minutes", "seating", "max_per_visitor"]


class TimeRangeForm(forms.ModelForm):
    class Meta:
        model = TimeRange
        fields = ["date", "start", "end"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "start": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "end": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
        }

    def clean(self):
        data = super().clean()
        if data.get("start") and data.get("end") and data["end"] <= data["start"]:
            raise forms.ValidationError("The end time must be after the start time.")
        return data


class BaseRangeFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        ranges = []
        for form in self.forms:
            data = getattr(form, "cleaned_data", None)
            if not data or data.get("DELETE") or not data.get("date"):
                continue
            if data.get("start") and data.get("end"):
                ranges.append((data["date"], data["start"], data["end"]))
        ranges.sort()
        for (d1, _s1, e1), (d2, s2, _e2) in zip(ranges, ranges[1:]):
            if d1 == d2 and s2 < e1:
                raise forms.ValidationError("Time ranges on the same day must not overlap.")


RangeFormSet = inlineformset_factory(
    Exhibition, TimeRange, form=TimeRangeForm, formset=BaseRangeFormSet, extra=3, can_delete=True
)
