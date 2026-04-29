from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Event, Budget, Expense, Volunteer, Sponsor, Feedback, LostFoundItem
from django.core.exceptions import ValidationError

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email', 'phone_number',)

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'date', 'start_time', 'end_time', 'venue', 'description', 'category', 'is_eco_friendly', 'image']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        venue = cleaned_data.get('venue')

        if start_time and end_time and start_time >= end_time:
            raise ValidationError("End time must be after start time.")

        if date and start_time and end_time and venue:
            # Check for overlapping events at the same venue on the same date
            overlapping_events = Event.objects.filter(
                date=date,
                venue=venue,
                start_time__lt=end_time,
                end_time__gt=start_time
            )
            
            # If editing an existing event, exclude it from the check
            if self.instance.pk:
                overlapping_events = overlapping_events.exclude(pk=self.instance.pk)

            if overlapping_events.exists():
                raise ValidationError("There is already an event scheduled at this venue during this time.")

        return cleaned_data

class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['total_budget']

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['description', 'amount', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

class VolunteerForm(forms.ModelForm):
    class Meta:
        model = Volunteer
        fields = ['student', 'role_description']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = User.objects.filter(role='Student')

class SponsorForm(forms.ModelForm):
    class Meta:
        model = Sponsor
        fields = ['name', 'logo', 'amount_contributed']

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['rating', 'comments']
        widgets = {
            'comments': forms.Textarea(attrs={'rows': 3}),
        }

class LostFoundForm(forms.ModelForm):
    class Meta:
        model = LostFoundItem
        fields = ['name', 'status', 'description', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
