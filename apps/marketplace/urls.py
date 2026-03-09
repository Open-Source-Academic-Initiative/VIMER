from django.urls import path
from .views import (
    ChallengeListView, 
    ChallengeDetailView, 
    ChallengeCreateView, 
    ApplicationCreateView
)

urlpatterns = [
    path('', ChallengeListView.as_view(), name='challenge-list'),
    path('challenge/create/', ChallengeCreateView.as_view(), name='challenge-create'),
    path('challenge/<int:pk>/', ChallengeDetailView.as_view(), name='challenge-detail'),
    path('challenge/<int:pk>/apply/', ApplicationCreateView.as_view(), name='challenge-apply'),
]
