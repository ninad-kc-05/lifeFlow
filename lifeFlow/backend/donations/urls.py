from django.urls import path

from .views import SubmitDonorSurveyView, DonorDashboardSummaryView, DonorDonationHistoryView


urlpatterns = [
    path("surveys/submit/", SubmitDonorSurveyView.as_view(), name="submit_donor_survey"),
    path("donor/dashboard-summary/", DonorDashboardSummaryView.as_view(), name="donor_dashboard_summary"),
    path("donor/donation-history/", DonorDonationHistoryView.as_view(), name="donor_donation_history"),
]
