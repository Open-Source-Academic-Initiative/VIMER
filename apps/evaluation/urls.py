from django.urls import path

from apps.evaluation.views import (
    ApplicationCriterionEvaluationUpdateView,
    AwardDecisionCreateView,
    ChallengeEvaluationStartView,
    ChallengeEvaluationRoleAssignmentUpdateView,
)

urlpatterns = [
    path(
        "challenge/<int:pk>/roles/",
        ChallengeEvaluationRoleAssignmentUpdateView.as_view(),
        name="challenge-evaluation-roles-update",
    ),
    path(
        "challenge/<int:pk>/start/",
        ChallengeEvaluationStartView.as_view(),
        name="challenge-evaluation-start",
    ),
    path(
        "challenge/<int:pk>/award/",
        AwardDecisionCreateView.as_view(),
        name="award-decision-create",
    ),
    path(
        "challenge/<int:pk>/application/<int:application_pk>/evaluate/",
        ApplicationCriterionEvaluationUpdateView.as_view(),
        name="application-criterion-evaluation-update",
    ),
]
