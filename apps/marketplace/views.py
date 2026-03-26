from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, FormView, ListView
from django.urls import reverse_lazy
from apps.corporate.models import Organization
from apps.evaluation.application.queries import (
    build_challenge_publisher_detail_read_model,
)
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

    def get_queryset(self):
        organization = getattr(self.request.user, "organization", None)
        return (
            Challenge.objects.visible_to_organization(organization)
            .select_related("publisher")
        )

class ChallengeDetailView(LoginRequiredMixin, DetailView):
    model = Challenge
    template_name = 'marketplace/challenge_detail.html'
    context_object_name = 'challenge'

    def get_queryset(self):
        organization = getattr(self.request.user, "organization", None)
        return (
            Challenge.objects.visible_to_organization(organization)
            .select_related("publisher")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        challenge = self.object
        detail_read_model = build_challenge_publisher_detail_read_model(
            challenge=challenge,
            requester=self.request.user,
        )
        context["evaluation_criteria_items"] = challenge.evaluation_criteria_list()
        context["award_decision"] = detail_read_model.award_decision
        context["timeline_entries"] = list(detail_read_model.timeline_entries)
        context["evaluation_role_assignments"] = list(
            detail_read_model.evaluation_role_assignments
        )
        context["evaluation_team"] = {
            "evaluators": list(detail_read_model.evaluation_team.evaluators),
            "adjudicator": detail_read_model.evaluation_team.adjudicator,
            "observers": list(detail_read_model.evaluation_team.observers),
        }
        context["challenge_applications"] = list(detail_read_model.challenge_applications)
        context["can_manage_evaluation_team"] = (
            detail_read_model.can_manage_evaluation_team
        )
        context["show_applicant_identity"] = detail_read_model.show_applicant_identity
        context["has_required_evaluation_team"] = (
            detail_read_model.has_required_evaluation_team
        )
        context["can_evaluate_applications"] = detail_read_model.can_evaluate_applications
        context["can_adjudicate_challenge"] = detail_read_model.can_adjudicate_challenge
        context["can_start_evaluation"] = detail_read_model.can_start_evaluation
        context["can_award_challenge"] = detail_read_model.can_award_challenge
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
