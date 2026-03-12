from django.urls import path
from . import views

urlpatterns = [
    path('api/auth/request-email-otp/', views.request_email_otp, name='request_email_otp'),
    path('api/auth/verify-email-otp/', views.verify_email_otp, name='verify_email_otp'),
]
