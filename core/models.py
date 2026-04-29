from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import qrcode
from io import BytesIO
from django.core.files import File

class User(AbstractUser):
    ROLE_CHOICES = (
        ('Admin', 'Admin'),
        ('Organizer', 'Organizer'),
        ('Student', 'Student'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Student')
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

class Event(models.fields.Field):
    pass # Replaced below

class Event(models.Model):
    title = models.CharField(max_length=200)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    venue = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=100)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events_organized')
    is_eco_friendly = models.BooleanField(default=False)
    image = models.ImageField(upload_to='event_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Registration(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registrations')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    registration_date = models.DateTimeField(auto_now_add=True)
    attended = models.BooleanField(default=False)

    class Meta:
        unique_together = ('student', 'event')

    def __str__(self):
        return f"{self.student.username} - {self.event.title}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new and not self.qr_code:
            # Generate QR Code after we have a pk
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            # URL to verify attendance (relative, assumes standard host)
            data = f"/events/verify/{self.pk}/"
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            file_name = f"qr_reg_{self.student.id}_{self.event.id}.png"
            self.qr_code.save(file_name, File(buffer), save=True)



class Certificate(models.Model):
    registration = models.OneToOneField(Registration, on_delete=models.CASCADE)
    file = models.FileField(upload_to='certificates/')
    issued_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Certificate for {self.registration.student.username}"

class Feedback(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='feedbacks')
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comments = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.event.title} by {self.student.username}"

class Budget(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE)
    total_budget = models.DecimalField(max_digits=10, decimal_places=2)
    amount_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    @property
    def remaining_balance(self):
        return self.total_budget - self.amount_spent

    def __str__(self):
        return f"Budget for {self.event.title}"

class Expense(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='expenses')
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.amount} - {self.description}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update budget amount_spent
        expenses = self.budget.expenses.all()
        total_spent = sum(expense.amount for expense in expenses)
        self.budget.amount_spent = total_spent
        self.budget.save()

class Volunteer(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='volunteers')
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    role_description = models.CharField(max_length=200)

    class Meta:
        unique_together = ('event', 'student')

    def __str__(self):
        return f"{self.student.username} - {self.event.title}"

class Sponsor(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='sponsors')
    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='sponsor_logos/', blank=True, null=True)
    amount_contributed = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return self.name

class LostFoundItem(models.Model):
    STATUS_CHOICES = (
        ('Lost', 'Lost'),
        ('Found', 'Found'),
        ('Claimed', 'Claimed'),
    )
    name = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Lost')
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    date_reported = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='lost_found/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.status}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}"
