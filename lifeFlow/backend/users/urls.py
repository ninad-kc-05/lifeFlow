from django.urls import path
from . import views

urlpatterns = [
    path('api/register/donor/', views.register_donor, name='register_donor'),
    path('api/register/hospital/', views.register_hospital, name='register_hospital'),
    path('api/register/admin/', views.register_admin, name='register_admin'),
    path('api/admin/users/', views.admin_users_list, name='admin_users_list'),
    path('api/admin/dashboard-summary/', views.admin_dashboard_summary, name='admin_dashboard_summary'),
]
