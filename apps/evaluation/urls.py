from django.urls import path

from apps.evaluation.views import AwardDecisionCreateView, ChallengeEvaluationStartView

urlpatterns = [
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
]
