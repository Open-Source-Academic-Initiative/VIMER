from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import FormView

from apps.corporate.models import Organization
from apps.marketplace.application.exceptions import (
    ChallengeApplicationValidationError,
    DuplicateChallengeApplicationError,
)
from apps.marketplace.application.services import (
    save_application_draft,
    submit_challenge_application,
)
from apps.marketplace.application_forms import ApplicationSubmissionForm
from apps.marketplace.challenge_views import RoleRequiredMixin
from apps.marketplace.models import Application, Challenge


class ApplicationCreateView(LoginRequiredMixin, RoleRequiredMixin, FormView):
    form_class = ApplicationSubmissionForm
    role_required = Organization.MarketRole.SUPPLY_SIDE
    template_name = "marketplace/application_form.html"

    def get_challenge(self):
        if not hasattr(self, "_challenge"):
            self._challenge = get_object_or_404(Challenge, pk=self.kwargs["pk"])
        return self._challenge

    def get_existing_application(self):
        if not hasattr(self, "_existing_application"):
            organization_id = getattr(self.request.user, "organization_id", None)
            self._existing_application = None
            if organization_id is not None:
                self._existing_application = Application.objects.filter(
                    challenge=self.get_challenge(),
                    applicant_id=organization_id,
                ).first()
        return self._existing_application

    def get_submission_intent(self):
        if self.request.method != "POST":
            return "submit"
        return "draft" if self.request.POST.get("intent") == "draft" else "submit"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["submission_intent"] = self.get_submission_intent()
        existing_application = self.get_existing_application()
        if (
            self.request.method == "GET"
            and existing_application is not None
            and existing_application.status == Application.Status.DRAFT
        ):
            kwargs["initial"] = {
                "problem_understanding": existing_application.problem_understanding,
                "proposed_solution": existing_application.proposed_solution,
                "capabilities_evidence": existing_application.capabilities_evidence,
                "execution_plan": existing_application.execution_plan,
            }
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["challenge"] = self.get_challenge()
        context["existing_application"] = self.get_existing_application()
        return context

    def get_success_url(self):
        if self.get_submission_intent() == "draft":
            return reverse("marketplace:challenge-apply", args=[self.get_challenge().pk])
        return reverse("marketplace:challenge-detail", args=[self.get_challenge().pk])

    def form_valid(self, form):
        existing_application = self.get_existing_application()
        if (
            existing_application is not None
            and existing_application.status == Application.Status.SUBMITTED
        ):
            form.add_error(
                None,
                "Tu organización ya envió una propuesta para este desafío.",
            )
            return self.form_invalid(form)

        try:
            if self.get_submission_intent() == "draft":
                save_application_draft(
                    challenge=self.get_challenge(),
                    applicant=self.request.user.organization,
                    command=form.to_draft_command(),
                )
                messages.success(
                    self.request,
                    "Tu borrador fue guardado y permanece privado hasta que lo envíes.",
                )
            else:
                submit_challenge_application(
                    challenge=self.get_challenge(),
                    applicant=self.request.user.organization,
                    command=form.to_command(),
                )
                messages.success(
                    self.request,
                    "Tu propuesta fue enviada y ya no puede modificarse.",
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
