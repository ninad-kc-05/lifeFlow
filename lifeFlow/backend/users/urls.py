from django.urls import path
from . import views

urlpatterns = [
    path('api/register/donor/', views.register_donor, name='register_donor'),
    path('api/register/hospital/', views.register_hospital, name='register_hospital'),
    path('api/register/admin/', views.register_admin, name='register_admin'),
    path('api/admin/users/', views.admin_users_list, name='admin_users_list'),
    path('api/admin/dashboard-summary/', views.admin_dashboard_summary, name='admin_dashboard_summary'),
    path('api/donor/profile/', views.get_donor_profile, name='get_donor_profile'),
    path('api/donor/profile/update/', views.update_donor_profile, name='update_donor_profile'),
    path('api/donor/status/update/', views.update_donor_status, name='update_donor_status'),
]
