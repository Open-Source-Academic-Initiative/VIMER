from pathlib import PurePath
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.http import FileResponse, HttpResponse, HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.http import content_disposition_header
from django.views import View
from django.views.generic import FormView

from apps.corporate.models import Organization
from apps.identity.mixins import OperationalUserRequiredMixin
from apps.marketplace.application.exceptions import (
    ChallengeApplicationValidationError,
    DuplicateChallengeApplicationError,
)
from apps.marketplace.application.services import (
    delete_application_draft_attachment,
    save_application_draft,
    submit_challenge_application,
)
from apps.marketplace.application_forms import ApplicationSubmissionForm
from apps.marketplace.challenge_views import RoleRequiredMixin
from apps.marketplace.models import Application, ApplicationAttachment, Challenge, ChallengeAttachment


def build_attachment_download_response(attachment, *, download_filename=None):
    """Serve a private attachment after the view has authorized the request.

    With ``ATTACHMENT_X_ACCEL_REDIRECT`` (production profile) the file body is
    delegated to nginx through the `internal` location; otherwise (pilot,
    development, tests) Django streams it directly.
    """
    filename = download_filename or attachment.original_filename
    if settings.ATTACHMENT_X_ACCEL_REDIRECT:
        response = HttpResponse()
        response["Content-Type"] = attachment.content_type or "application/octet-stream"
        response["Content-Disposition"] = content_disposition_header(
            as_attachment=True,
            filename=filename,
        )
        response["X-Accel-Redirect"] = quote(f"/media/{attachment.file.name}")
        return response
    return FileResponse(
        attachment.file.open("rb"),
        as_attachment=True,
        filename=filename,
    )


class ApplicationCreateView(OperationalUserRequiredMixin, RoleRequiredMixin, FormView):
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
        kwargs["challenge"] = self.get_challenge()
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
                "offered_amount": existing_application.offered_amount,
                "offer_currency": (
                    existing_application.offer_currency
                    or self.get_challenge().budget_currency
                ),
                "estimated_duration_days": existing_application.estimated_duration_days,
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


class ChallengeAttachmentDownloadView(View):
    def get(self, request, *args, **kwargs):
        attachment = get_object_or_404(
            ChallengeAttachment.objects.select_related("challenge"),
            opaque_id=kwargs["opaque_id"],
        )
        is_operational_publisher = (
            request.user.is_authenticated
            and request.user.is_operational_member_of(
                attachment.challenge.publisher_id
            )
        )
        if (
            attachment.challenge.status
            not in Challenge.publicly_visible_statuses()
            and not is_operational_publisher
        ):
            return HttpResponseForbidden()
        return build_attachment_download_response(attachment)


class ApplicationAttachmentDownloadView(OperationalUserRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        attachment = get_object_or_404(
            ApplicationAttachment.objects.select_related(
                "application__challenge",
                "application__applicant",
            ),
            opaque_id=kwargs["opaque_id"],
        )
        application = attachment.application
        challenge = application.challenge
        is_applicant = request.user.is_operational_member_of(
            application.applicant_id
        )
        is_operational_publisher = request.user.is_operational_member_of(
            challenge.publisher_id
        )
        is_evaluation_team = (
            is_operational_publisher
            and challenge.status
            in {
                Challenge.Status.CLOSED,
                Challenge.Status.UNDER_EVALUATION,
                Challenge.Status.DESERTED,
            }
            and challenge.evaluation_role_assignments.filter(
                user=request.user
            ).exists()
        )
        publisher_can_open_awarded_file = (
            is_operational_publisher
            and challenge.status == Challenge.Status.AWARDED
        )
        if not (
            is_applicant
            or is_evaluation_team
            or publisher_can_open_awarded_file
        ):
            return self.handle_no_permission()
        download_filename = attachment.original_filename
        if is_evaluation_team and challenge.status != Challenge.Status.AWARDED:
            extension = PurePath(attachment.original_filename).suffix.lower()
            download_filename = f"adjunto-propuesta-{attachment.opaque_id}{extension}"
        return build_attachment_download_response(
            attachment,
            download_filename=download_filename,
        )


class ApplicationAttachmentDeleteView(OperationalUserRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        if request.POST.get("confirm") != "on":
            messages.error(
                request,
                "Debes confirmar explícitamente la eliminación del adjunto.",
            )
            return HttpResponseRedirect(reverse("marketplace:challenge-list"))
        try:
            attachment = delete_application_draft_attachment(
                opaque_id=kwargs["opaque_id"],
                organization=getattr(request.user, "organization", None),
            )
        except ChallengeApplicationValidationError as exc:
            for message in exc.messages:
                messages.error(request, message)
            return HttpResponseRedirect(reverse("marketplace:challenge-list"))

        messages.success(request, "El adjunto fue eliminado del borrador.")
        return HttpResponseRedirect(
            reverse(
                "marketplace:challenge-apply",
                args=[attachment.application.challenge_id],
            )
        )
