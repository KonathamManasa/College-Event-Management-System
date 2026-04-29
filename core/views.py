from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, EventForm, BudgetForm, ExpenseForm, VolunteerForm, SponsorForm, FeedbackForm, LostFoundForm
from .models import User, Event, Registration, Certificate, Budget, Expense, Volunteer, Sponsor, Feedback, LostFoundItem, Notification
from django.contrib import messages
from django.http import HttpResponse, FileResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from io import BytesIO
from django.core.files.base import ContentFile
import qrcode

def home(request):
    return render(request, 'core/home.html')

def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful.")
            return redirect('dashboard')
        else:
            messages.error(request, "Unsuccessful registration. Invalid information.")
    else:
        form = CustomUserCreationForm()
    return render(request, 'core/register.html', {'form': form})

@login_required
def dashboard(request):
    if request.user.role == 'Admin' or request.user.is_superuser:
        context = {
            'total_users': User.objects.count(),
            'total_events': Event.objects.count(),
            'total_registrations': Registration.objects.count(),
            'total_lost_found': LostFoundItem.objects.count()
        }
        return render(request, 'core/dashboard_admin.html', context)
    elif request.user.role == 'Organizer':
        return render(request, 'core/dashboard_organizer.html')
    else:
        return render(request, 'core/dashboard_student.html')

def event_list(request):
    events = Event.objects.all().order_by('date', 'start_time')
    return render(request, 'core/event_list.html', {'events': events})

def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    is_registered = False
    if request.user.is_authenticated:
        is_registered = event.registrations.filter(student=request.user).exists()
    return render(request, 'core/event_detail.html', {'event': event, 'is_registered': is_registered})

@login_required
def event_create(request):
    if request.user.role not in ['Admin', 'Organizer']:
        messages.error(request, "You do not have permission to create events.")
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            messages.success(request, "Event created successfully!")
            return redirect('dashboard')
    else:
        form = EventForm()
    return render(request, 'core/event_form.html', {'form': form, 'title': 'Create Event'})

@login_required
def event_update(request, pk):
    event = get_object_or_404(Event, pk=pk)
    
    if request.user != event.organizer and request.user.role != 'Admin':
        messages.error(request, "You do not have permission to edit this event.")
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, "Event updated successfully!")
            return redirect('dashboard')
    else:
        form = EventForm(instance=event)
    return render(request, 'core/event_form.html', {'form': form, 'title': 'Edit Event'})

@login_required
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    
    if request.user != event.organizer and request.user.role != 'Admin':
        messages.error(request, "You do not have permission to delete this event.")
        return redirect('dashboard')
        
    if request.method == 'POST':
        event.delete()
        messages.success(request, "Event deleted successfully!")
        return redirect('dashboard')
    return render(request, 'core/event_confirm_delete.html', {'event': event})

@login_required
def event_register(request, pk):
    event = get_object_or_404(Event, pk=pk)
    
    if request.user.role != 'Student':
        messages.error(request, "Only students can register for events.")
        return redirect('event_detail', pk=pk)
        
    if request.method == 'POST':
        # Check if already registered
        if Registration.objects.filter(student=request.user, event=event).exists():
            messages.info(request, "You are already registered for this event.")
        else:
            Registration.objects.create(student=request.user, event=event)
            messages.success(request, f"Successfully registered for {event.title}! Check your dashboard for the QR code.")
            
    return redirect('event_detail', pk=pk)

@login_required
def verify_attendance(request, reg_id):
    if request.user.role not in ['Admin', 'Organizer']:
        messages.error(request, "You do not have permission to verify attendance.")
        return redirect('dashboard')
        
    registration = get_object_or_404(Registration, pk=reg_id)
    
    # Check if the user is the organizer of this event or an Admin
    if request.user != registration.event.organizer and request.user.role != 'Admin':
        messages.error(request, "You can only verify attendance for your own events.")
        return redirect('dashboard')
        
    if request.method == 'POST':
        registration.attended = True
        registration.save()
        messages.success(request, f"Attendance verified for {registration.student.get_full_name() or registration.student.username} at {registration.event.title}.")
        return redirect('dashboard')
        
    return render(request, 'core/verify_attendance.html', {'registration': registration})

@login_required
def self_check_in(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    
    if request.user.role != 'Student':
        messages.error(request, "Only students can check in to events.")
        return redirect('dashboard')
        
    registration, created = Registration.objects.get_or_create(
        student=request.user, 
        event=event
    )
    
    if not registration.attended:
        registration.attended = True
        registration.save()
        if created:
            messages.success(request, f"Successfully registered and checked in for {event.title}!")
        else:
            messages.success(request, f"Successfully checked in for {event.title}! You can now download your certificate.")
    else:
        messages.info(request, "You are already checked in for this event.")
        
    return redirect('dashboard')

@login_required
def generate_certificate(request, reg_id):
    registration = get_object_or_404(Registration, pk=reg_id, student=request.user)
    
    if not registration.attended:
        messages.error(request, "You must attend the event to receive a certificate.")
        return redirect('dashboard')
        
    # Check if certificate already exists
    if hasattr(registration, 'certificate'):
        return FileResponse(registration.certificate.file.open('rb'), content_type='application/pdf')
        
    # Generate new PDF certificate
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(letter))
    
    # Draw certificate background/border
    p.setStrokeColorRGB(0.2, 0.4, 0.8)
    p.setLineWidth(10)
    p.rect(0.5*inch, 0.5*inch, 10*inch, 7.5*inch)
    p.setStrokeColorRGB(0.8, 0.6, 0.2)
    p.setLineWidth(3)
    p.rect(0.6*inch, 0.6*inch, 9.8*inch, 7.3*inch)
    
    # Text content
    p.setFont("Helvetica-Bold", 48)
    p.drawCentredString(5.5*inch, 6*inch, "Certificate of Participation")
    
    p.setFont("Helvetica", 24)
    p.drawCentredString(5.5*inch, 5*inch, "This is to certify that")
    
    p.setFont("Helvetica-Bold", 32)
    student_name = request.user.get_full_name() or request.user.username
    p.drawCentredString(5.5*inch, 4*inch, student_name.upper())
    
    p.setFont("Helvetica", 24)
    p.drawCentredString(5.5*inch, 3*inch, "has successfully participated in the event")
    
    p.setFont("Helvetica-Bold", 28)
    p.drawCentredString(5.5*inch, 2*inch, registration.event.title)
    
    p.setFont("Helvetica", 16)
    p.drawCentredString(5.5*inch, 1.2*inch, f"Date: {registration.event.date}")
    
    p.showPage()
    p.save()
    
    pdf_value = buffer.getvalue()
    buffer.close()
    
    cert = Certificate(registration=registration)
    file_name = f"certificate_{registration.id}.pdf"
    cert.file.save(file_name, ContentFile(pdf_value), save=True)
    
    messages.success(request, "Certificate generated successfully!")
    return FileResponse(cert.file.open('rb'), content_type='application/pdf')

@login_required
def manage_budget(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if request.user != event.organizer and request.user.role != 'Admin':
        messages.error(request, "You do not have permission to view this budget.")
        return redirect('dashboard')
        
    budget, created = Budget.objects.get_or_create(event=event, defaults={'total_budget': 0})
    
    if request.method == 'POST' and 'update_budget' in request.POST:
        budget_form = BudgetForm(request.POST, instance=budget)
        if budget_form.is_valid():
            budget_form.save()
            messages.success(request, "Budget updated successfully!")
            return redirect('manage_budget', event_id=event.id)
    else:
        budget_form = BudgetForm(instance=budget)
        
    expense_form = ExpenseForm()
    expenses = budget.expenses.all().order_by('-date')
    
    return render(request, 'core/manage_budget.html', {
        'event': event,
        'budget': budget,
        'budget_form': budget_form,
        'expense_form': expense_form,
        'expenses': expenses
    })

@login_required
def add_expense(request, budget_id):
    budget = get_object_or_404(Budget, pk=budget_id)
    if request.user != budget.event.organizer and request.user.role != 'Admin':
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.budget = budget
            expense.save()
            messages.success(request, "Expense added successfully!")
            
    return redirect('manage_budget', event_id=budget.event.id)

@login_required
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, pk=expense_id)
    if request.user != expense.budget.event.organizer and request.user.role != 'Admin':
        return redirect('dashboard')
        
    event_id = expense.budget.event.id
    if request.method == 'POST':
        expense.delete()
        messages.success(request, "Expense deleted successfully!")
        
    return redirect('manage_budget', event_id=event_id)

@login_required
def manage_volunteers(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if request.user != event.organizer and request.user.role != 'Admin':
        messages.error(request, "Permission denied.")
        return redirect('dashboard')
        
    volunteers = event.volunteers.all()
    form = VolunteerForm()
    
    return render(request, 'core/manage_volunteers.html', {
        'event': event,
        'volunteers': volunteers,
        'form': form
    })

@login_required
def manage_attendees(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if request.user != event.organizer and request.user.role != 'Admin':
        messages.error(request, "Permission denied.")
        return redirect('dashboard')
        
    registrations = event.registrations.all().order_by('-registration_date')
    
    return render(request, 'core/manage_attendees.html', {
        'event': event,
        'registrations': registrations
    })

@login_required
def event_qr_image(request, event_id):
    from django.urls import reverse
    event = get_object_or_404(Event, pk=event_id)
    
    # Generate the absolute URL so phones can open it
    checkin_url = request.build_absolute_uri(reverse('self_check_in', args=[event.id]))
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(checkin_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    response = HttpResponse(content_type="image/png")
    img.save(response, "PNG")
    return response

@login_required
def add_volunteer(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if request.user != event.organizer and request.user.role != 'Admin':
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = VolunteerForm(request.POST)
        if form.is_valid():
            volunteer = form.save(commit=False)
            volunteer.event = event
            try:
                volunteer.save()
                messages.success(request, "Volunteer added successfully!")
            except:
                messages.error(request, "Student is already a volunteer for this event.")
                
    return redirect('manage_volunteers', event_id=event.id)

@login_required
def delete_volunteer(request, volunteer_id):
    volunteer = get_object_or_404(Volunteer, pk=volunteer_id)
    if request.user != volunteer.event.organizer and request.user.role != 'Admin':
        return redirect('dashboard')
        
    event_id = volunteer.event.id
    if request.method == 'POST':
        volunteer.delete()
        messages.success(request, "Volunteer removed successfully!")
        
    return redirect('manage_volunteers', event_id=event_id)

@login_required
def manage_sponsors(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if request.user != event.organizer and request.user.role != 'Admin':
        messages.error(request, "Permission denied.")
        return redirect('dashboard')
        
    sponsors = event.sponsors.all()
    form = SponsorForm()
    
    return render(request, 'core/manage_sponsors.html', {
        'event': event,
        'sponsors': sponsors,
        'form': form
    })

@login_required
def add_sponsor(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if request.user != event.organizer and request.user.role != 'Admin':
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = SponsorForm(request.POST, request.FILES)
        if form.is_valid():
            sponsor = form.save(commit=False)
            sponsor.event = event
            sponsor.save()
            messages.success(request, "Sponsor added successfully!")
                
    return redirect('manage_sponsors', event_id=event.id)

@login_required
def delete_sponsor(request, sponsor_id):
    sponsor = get_object_or_404(Sponsor, pk=sponsor_id)
    if request.user != sponsor.event.organizer and request.user.role != 'Admin':
        return redirect('dashboard')
        
    event_id = sponsor.event.id
    if request.method == 'POST':
        sponsor.delete()
        messages.success(request, "Sponsor removed successfully!")
        
    return redirect('manage_sponsors', event_id=event_id)

@login_required
def add_feedback(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    registration = Registration.objects.filter(student=request.user, event=event, attended=True).first()
    
    if not registration:
        messages.error(request, "You must attend the event to leave feedback.")
        return redirect('event_detail', pk=event.pk)
        
    # Check if already left feedback
    if Feedback.objects.filter(student=request.user, event=event).exists():
        messages.info(request, "You have already submitted feedback for this event.")
        return redirect('event_detail', pk=event.pk)
        
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.event = event
            feedback.student = request.user
            feedback.save()
            messages.success(request, "Thank you for your feedback!")
            return redirect('event_detail', pk=event.pk)
    else:
        form = FeedbackForm()
        
    return render(request, 'core/add_feedback.html', {'form': form, 'event': event})

def lost_found_list(request):
    items = LostFoundItem.objects.all().order_by('-date_reported')
    return render(request, 'core/lost_found_list.html', {'items': items})

@login_required
def post_lost_found(request):
    if request.method == 'POST':
        form = LostFoundForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.reported_by = request.user
            item.save()
            messages.success(request, "Item posted successfully!")
            return redirect('lost_found_list')
    else:
        form = LostFoundForm()
    return render(request, 'core/post_lost_found.html', {'form': form})

@login_required
def update_lost_found_status(request, item_id):
    item = get_object_or_404(LostFoundItem, pk=item_id)
    if request.user != item.reported_by and request.user.role != 'Admin':
        messages.error(request, "Permission denied.")
        return redirect('lost_found_list')
        
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(LostFoundItem.STATUS_CHOICES):
            item.status = new_status
            item.save()
            messages.success(request, "Status updated successfully!")
    return redirect('lost_found_list')

@login_required
def notifications_list(request):
    notifications = request.user.notifications.all().order_by('-created_at')
    # Mark all as read when viewed
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'core/notifications_list.html', {'notifications': notifications})

@login_required
def send_notification(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if request.user != event.organizer and request.user.role != 'Admin':
        messages.error(request, "Permission denied.")
        return redirect('dashboard')
        
    if request.method == 'POST':
        message = request.POST.get('message')
        if message:
            registrations = event.registrations.all()
            for reg in registrations:
                Notification.objects.create(
                    user=reg.student,
                    message=f"[{event.title}] {message}"
                )
            messages.success(request, f"Notification sent to {registrations.count()} attendees.")
    return redirect('event_detail', pk=event.pk)

@login_required
def manage_users(request):
    if request.user.role != 'Admin' and not request.user.is_superuser:
        messages.error(request, "Access denied. Admins only.")
        return redirect('dashboard')
        
    users = User.objects.all().exclude(id=request.user.id).order_by('-date_joined')
    return render(request, 'core/manage_users.html', {'users': users})

@login_required
def toggle_user_status(request, user_id):
    if request.user.role != 'Admin' and not request.user.is_superuser:
        return redirect('dashboard')
        
    if request.method == 'POST':
        target_user = get_object_or_404(User, pk=user_id)
        if not target_user.is_superuser:  # Prevent deactivating superusers
            target_user.is_active = not target_user.is_active
            target_user.save()
            status = "activated" if target_user.is_active else "deactivated"
            messages.success(request, f"User {target_user.username} successfully {status}.")
            
    return redirect('manage_users')

@login_required
def change_user_role(request, user_id):
    if request.user.role != 'Admin' and not request.user.is_superuser:
        return redirect('dashboard')
        
    if request.method == 'POST':
        target_user = get_object_or_404(User, pk=user_id)
        new_role = request.POST.get('role')
        if new_role in dict(User.ROLE_CHOICES) and not target_user.is_superuser:
            target_user.role = new_role
            target_user.save()
            messages.success(request, f"User {target_user.username}'s role changed to {new_role}.")
            
    return redirect('manage_users')

@login_required
def admin_events(request):
    if request.user.role != 'Admin' and not request.user.is_superuser:
        return redirect('dashboard')
        
    events = Event.objects.all().order_by('-date')
    return render(request, 'core/admin_events.html', {'events': events})
