from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Event, Registration, Certificate, Feedback,
    Budget, Expense, Volunteer, Sponsor, LostFoundItem, Notification
)

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'phone_number')}),
    )

admin.site.register(User, CustomUserAdmin)
admin.site.register(Event)
admin.site.register(Registration)
admin.site.register(Certificate)
admin.site.register(Feedback)
admin.site.register(Budget)
admin.site.register(Expense)
admin.site.register(Volunteer)
admin.site.register(Sponsor)
admin.site.register(LostFoundItem)
admin.site.register(Notification)
