from django.urls import path
from apps.marketplace.application_views import (
    ApplicationAttachmentDownloadView,
    ApplicationCreateView,
    ChallengeAttachmentDownloadView,
)
from apps.marketplace.challenge_views import (
    ChallengeCreateView,
    ChallengeDetailView,
    ChallengeListView,
)

urlpatterns = [
    path("", ChallengeListView.as_view(), name="challenge-list"),
    path("challenge/create/", ChallengeCreateView.as_view(), name="challenge-create"),
    path("challenge/<int:pk>/", ChallengeDetailView.as_view(), name="challenge-detail"),
    path("challenge/<int:pk>/apply/", ApplicationCreateView.as_view(), name="challenge-apply"),
    path("attachments/challenge/<str:opaque_id>/", ChallengeAttachmentDownloadView.as_view(), name="challenge-attachment-download"),
    path("attachments/application/<str:opaque_id>/", ApplicationAttachmentDownloadView.as_view(), name="application-attachment-download"),
]
