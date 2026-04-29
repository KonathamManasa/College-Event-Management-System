from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('events/', views.event_list, name='event_list'),
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
    path('events/create/', views.event_create, name='event_create'),
    path('events/<int:pk>/edit/', views.event_update, name='event_update'),
    path('events/<int:pk>/delete/', views.event_delete, name='event_delete'),
    path('events/<int:pk>/register/', views.event_register, name='event_register'),
    path('events/verify/<int:reg_id>/', views.verify_attendance, name='verify_attendance'),
    path('events/certificate/<int:reg_id>/', views.generate_certificate, name='generate_certificate'),
    path('events/<int:event_id>/budget/', views.manage_budget, name='manage_budget'),
    path('budget/<int:budget_id>/expense/add/', views.add_expense, name='add_expense'),
    path('expense/<int:expense_id>/delete/', views.delete_expense, name='delete_expense'),
    path('events/<int:event_id>/volunteers/', views.manage_volunteers, name='manage_volunteers'),
    path('events/<int:event_id>/volunteers/add/', views.add_volunteer, name='add_volunteer'),
    path('volunteers/<int:volunteer_id>/delete/', views.delete_volunteer, name='delete_volunteer'),
    path('events/<int:event_id>/sponsors/', views.manage_sponsors, name='manage_sponsors'),
    path('events/<int:event_id>/sponsors/add/', views.add_sponsor, name='add_sponsor'),
    path('sponsors/<int:sponsor_id>/delete/', views.delete_sponsor, name='delete_sponsor'),
    path('events/<int:event_id>/feedback/add/', views.add_feedback, name='add_feedback'),
    path('lost-found/', views.lost_found_list, name='lost_found_list'),
    path('lost-found/post/', views.post_lost_found, name='post_lost_found'),
    path('lost-found/<int:item_id>/status/', views.update_lost_found_status, name='update_lost_found_status'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('events/<int:event_id>/notifications/send/', views.send_notification, name='send_notification'),
]
