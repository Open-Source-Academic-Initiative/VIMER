from django.urls import path
from apps.marketplace.application_views import (
    ApplicationAttachmentDeleteView,
    ApplicationAttachmentDownloadView,
    ApplicationCreateView,
    ChallengeAttachmentDownloadView,
)
from apps.marketplace.challenge_views import (
    ChallengeCancelView,
    ChallengeCloseView,
    ChallengeCreateView,
    ChallengeDesertView,
    ChallengeDetailView,
    ChallengeDraftUpdateView,
    ChallengeListView,
    ChallengePublishView,
    MyApplicationsView,
    MyChallengesView,
)

urlpatterns = [
    path("", ChallengeListView.as_view(), name="challenge-list"),
    path("challenge/create/", ChallengeCreateView.as_view(), name="challenge-create"),
    path("my-challenges/", MyChallengesView.as_view(), name="my-challenges"),
    path("my-applications/", MyApplicationsView.as_view(), name="my-applications"),
    path("challenge/<int:pk>/", ChallengeDetailView.as_view(), name="challenge-detail"),
    path("challenge/<int:pk>/edit/", ChallengeDraftUpdateView.as_view(), name="challenge-edit"),
    path("challenge/<int:pk>/publish/", ChallengePublishView.as_view(), name="challenge-publish"),
    path("challenge/<int:pk>/close/", ChallengeCloseView.as_view(), name="challenge-close"),
    path("challenge/<int:pk>/cancel/", ChallengeCancelView.as_view(), name="challenge-cancel"),
    path("challenge/<int:pk>/desert/", ChallengeDesertView.as_view(), name="challenge-desert"),
    path("challenge/<int:pk>/apply/", ApplicationCreateView.as_view(), name="challenge-apply"),
    path("attachments/challenge/<str:opaque_id>/", ChallengeAttachmentDownloadView.as_view(), name="challenge-attachment-download"),
    path("attachments/application/<str:opaque_id>/", ApplicationAttachmentDownloadView.as_view(), name="application-attachment-download"),
    path("attachments/application/<str:opaque_id>/delete/", ApplicationAttachmentDeleteView.as_view(), name="application-attachment-delete"),
]
