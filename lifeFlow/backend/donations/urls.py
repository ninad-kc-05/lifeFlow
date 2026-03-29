from django.urls import path

from .views import SubmitDonorSurveyView


urlpatterns = [
    path("surveys/submit/", SubmitDonorSurveyView.as_view(), name="submit_donor_survey"),
]
