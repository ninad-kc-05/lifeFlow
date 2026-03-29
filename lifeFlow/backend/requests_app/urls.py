from django.urls import path

from .views import (
    CreateBloodRequestView,
    ListBloodRequestView,
    UpdateBloodRequestStatusView,
)


urlpatterns = [
    path("requests/create/", CreateBloodRequestView.as_view(), name="create_blood_request"),
    path("requests/", ListBloodRequestView.as_view(), name="list_blood_requests"),
    path("requests/<int:id>/status/", UpdateBloodRequestStatusView.as_view(), name="update_blood_request_status"),
]
