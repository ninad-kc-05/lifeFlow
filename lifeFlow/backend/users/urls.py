from django.urls import path
from . import views

urlpatterns = [
    path('api/register/donor/', views.register_donor, name='register_donor'),
    path('api/register/hospital/', views.register_hospital, name='register_hospital'),
    path('api/register/admin/', views.register_admin, name='register_admin'),
]
