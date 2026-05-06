from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View
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
from apps.marketplace.models import Application, ApplicationAttachment, Challenge, ChallengeAttachment


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
                    actor=self.request.user,
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
                    actor=self.request.user,
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


class ChallengeAttachmentDownloadView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        attachment = get_object_or_404(
            ChallengeAttachment.objects.select_related("challenge"),
            opaque_id=kwargs["opaque_id"],
        )
        organization = getattr(request.user, "organization", None)
        if attachment.challenge.status == Challenge.Status.DRAFT and (
            organization is None or organization.pk != attachment.challenge.publisher_id
        ):
            return self.handle_no_permission()
        return FileResponse(
            attachment.file.open("rb"),
            as_attachment=True,
            filename=attachment.original_filename,
        )


class ApplicationAttachmentDownloadView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        attachment = get_object_or_404(
            ApplicationAttachment.objects.select_related(
                "application__challenge",
                "application__applicant",
            ),
            opaque_id=kwargs["opaque_id"],
        )
        organization_id = getattr(request.user, "organization_id", None)
        application = attachment.application
        challenge = application.challenge
        is_applicant = organization_id == application.applicant_id
        is_publisher = organization_id == challenge.publisher_id
        is_evaluation_team = challenge.evaluation_role_assignments.filter(
            user=request.user
        ).exists()
        if not (is_applicant or is_publisher or is_evaluation_team):
            return self.handle_no_permission()
        return FileResponse(
            attachment.file.open("rb"),
            as_attachment=True,
            filename=attachment.original_filename,
        )
