from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import FormView

from apps.corporate.models import Organization
from apps.marketplace.application.exceptions import (
    ChallengeApplicationValidationError,
    DuplicateChallengeApplicationError,
)
from apps.marketplace.application.services import submit_challenge_application
from apps.marketplace.application_forms import ApplicationSubmissionForm
from apps.marketplace.challenge_views import RoleRequiredMixin
from apps.marketplace.models import Challenge


class ApplicationCreateView(LoginRequiredMixin, RoleRequiredMixin, FormView):
    form_class = ApplicationSubmissionForm
    role_required = Organization.MarketRole.SUPPLY_SIDE
    template_name = "marketplace/application_form.html"
    success_url = reverse_lazy("marketplace:challenge-list")

    def get_challenge(self):
        if not hasattr(self, "_challenge"):
            self._challenge = get_object_or_404(Challenge, pk=self.kwargs["pk"])
        return self._challenge

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["challenge"] = self.get_challenge()
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
