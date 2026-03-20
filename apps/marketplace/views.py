from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, FormView, ListView
from django.urls import reverse_lazy
from apps.corporate.models import Organization
from apps.evaluation.application.queries import (
    build_challenge_application_evaluation_summaries,
)
from apps.evaluation.models import AwardDecision, ChallengeTimelineEntry
from apps.marketplace.application.exceptions import (
    ChallengeApplicationValidationError,
    DuplicateChallengeApplicationError,
)
from apps.marketplace.application.services import (
    publish_challenge,
    submit_challenge_application,
)
from apps.marketplace.forms import ApplicationSubmissionForm, ChallengePublicationForm
from .models import Challenge

class RoleRequiredMixin(UserPassesTestMixin):
    role_required = None
    
    def test_func(self):
        return (
            self.request.user.is_authenticated and 
            self.request.user.organization and 
            self.request.user.organization.role == self.role_required
        )

class ChallengeListView(LoginRequiredMixin, ListView):
    model = Challenge
    template_name = 'marketplace/challenge_list.html'
    context_object_name = 'challenges'

class ChallengeDetailView(LoginRequiredMixin, DetailView):
    model = Challenge
    template_name = 'marketplace/challenge_detail.html'
    context_object_name = 'challenge'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        challenge = self.object
        user_org = getattr(self.request.user, "organization", None)
        context["award_decision"] = AwardDecision.objects.filter(
            challenge=challenge
        ).select_related(
            "winning_application__applicant",
            "decided_by",
        ).first()
        context["timeline_entries"] = ChallengeTimelineEntry.objects.filter(
            challenge=challenge
        ).select_related(
            "actor",
            "award_decision__winning_application__applicant",
        )
        context["evaluation_criteria_items"] = challenge.evaluation_criteria_list()
        context["challenge_applications"] = build_challenge_application_evaluation_summaries(
            challenge
        )
        context["can_start_evaluation"] = (
            user_org is not None
            and challenge.publisher_id == user_org.pk
            and challenge.status == Challenge.Status.PUBLISHED
            and challenge.applications.exists()
            and context["award_decision"] is None
        )
        context["can_award_challenge"] = (
            user_org is not None
            and challenge.publisher_id == user_org.pk
            and challenge.status == Challenge.Status.UNDER_EVALUATION
            and challenge.applications.exists()
            and context["award_decision"] is None
        )
        return context

class ChallengeCreateView(LoginRequiredMixin, RoleRequiredMixin, FormView):
    form_class = ChallengePublicationForm
    role_required = Organization.MarketRole.DEMAND_SIDE
    template_name = 'marketplace/challenge_form.html'
    success_url = reverse_lazy("marketplace:challenge-list")

    def form_valid(self, form):
        publish_challenge(
            publisher=self.request.user.organization,
            command=form.to_command(),
        )
        return HttpResponseRedirect(self.get_success_url())

class ApplicationCreateView(LoginRequiredMixin, RoleRequiredMixin, FormView):
    form_class = ApplicationSubmissionForm
    role_required = Organization.MarketRole.SUPPLY_SIDE
    template_name = 'marketplace/application_form.html'
    success_url = reverse_lazy('marketplace:challenge-list')

    def get_challenge(self):
        if not hasattr(self, '_challenge'):
            self._challenge = get_object_or_404(Challenge, pk=self.kwargs['pk'])
        return self._challenge

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['challenge'] = self.get_challenge()
        return context

    def form_valid(self, form):
        try:
            submit_challenge_application(
                challenge=self.get_challenge(),
                applicant=self.request.user.organization,
                command=form.to_command(),
            )
        except DuplicateChallengeApplicationError:
            form.add_error(
                None,
                "Tu organización ya envió una propuesta para este desafío.",
            )
            return self.form_invalid(form)
        except ChallengeApplicationValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        return HttpResponseRedirect(self.get_success_url())
