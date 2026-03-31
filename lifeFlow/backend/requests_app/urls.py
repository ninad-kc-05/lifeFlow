from django.urls import path

from .views import (
    AdminAllocateDonorView,
    AdminApproveRequestView,
    AdminBloodRequestListView,
    AdminInventoryAllotView,
    AdminMarkReadRequestView,
    AdminRejectRequestView,
    AdminRequestDonorsView,
    AdminSearchDonorView,
    AssignTopDonorsView,
    CompleteDonationView,
    CreateBloodRequestView,
    DonorAcceptScheduleView,
    DonorActiveRequestView,
    DonorRespondView,
    HospitalAcceptedDonorsView,
    HospitalAcknowledgeDonorView,
    HospitalReturnToInventoryView,
    HospitalSelectDonorView,
    ListBloodRequestView,
    MatchDonorsView,
    UpdateBloodRequestStatusView,
)


urlpatterns = [
    path("create-request/", CreateBloodRequestView.as_view(), name="smart_create_request"),
    path("match-donors/<int:request_id>/", MatchDonorsView.as_view(), name="match_donors"),
    path("assign-top-donors/<int:request_id>/", AssignTopDonorsView.as_view(), name="assign_top_donors"),
    path("hospital-select-donor/", HospitalSelectDonorView.as_view(), name="hospital_select_donor"),
    path("complete-donation/", CompleteDonationView.as_view(), name="complete_donation"),

    path("admin/requests/", AdminBloodRequestListView.as_view(), name="admin_list_requests"),
    path("admin/requests/<int:id>/mark-read/", AdminMarkReadRequestView.as_view(), name="admin_mark_read_request"),
    path("admin/requests/<int:id>/approve/", AdminApproveRequestView.as_view(), name="admin_approve_request"),
    path("admin/requests/<int:id>/reject/", AdminRejectRequestView.as_view(), name="admin_reject_request"),
    path("admin/requests/<int:id>/allot-inventory/", AdminInventoryAllotView.as_view(), name="admin_allot_inventory"),
    path("admin/requests/<int:id>/search-donor/", AdminSearchDonorView.as_view(), name="admin_search_donor"),
    path("admin/requests/<int:id>/donors/", AdminRequestDonorsView.as_view(), name="admin_request_donors"),
    path("admin/allocate-donor/", AdminAllocateDonorView.as_view(), name="admin_allocate_donor"),
    path("hospital/accepted-donors/", HospitalAcceptedDonorsView.as_view(), name="hospital_accepted_donors"),
    path("hospital/acknowledge-donor/", HospitalAcknowledgeDonorView.as_view(), name="hospital_acknowledge_donor"),
    path("hospital/return-inventory/", HospitalReturnToInventoryView.as_view(), name="hospital_return_inventory"),
    path("donor/active-request/", DonorActiveRequestView.as_view(), name="donor_active_request"),
    path("donor/accept-schedule/", DonorAcceptScheduleView.as_view(), name="donor_accept_schedule"),
    path("donor/respond/", DonorRespondView.as_view(), name="donor_respond"),

    path("requests/create/", CreateBloodRequestView.as_view(), name="create_blood_request"),
    path("requests/", ListBloodRequestView.as_view(), name="list_blood_requests"),
    path("requests/<int:id>/status/", UpdateBloodRequestStatusView.as_view(), name="update_blood_request_status"),
]
