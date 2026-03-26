from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import FormView

from apps.evaluation.application.exceptions import ChallengeEvaluationValidationError
from apps.evaluation.application.queries import (
    build_challenge_application_evaluation_summaries,
    build_pending_award_messages,
)
from apps.evaluation.application.services import (
    assign_challenge_evaluation_roles,
    adjudicate_challenge,
    evaluate_application_by_criteria,
    start_challenge_evaluation,
)
from apps.evaluation.domain.blind_references import get_application_blind_reference
from apps.evaluation.forms import (
    ApplicationCriterionEvaluationForm,
    AwardDecisionForm,
    ChallengeEvaluationRoleAssignmentForm,
)
from apps.evaluation.models import ChallengeEvaluationRoleAssignment
from apps.marketplace.models import Application, Challenge


class ChallengePublisherRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def get_challenge(self):
        if not hasattr(self, "_challenge"):
            self._challenge = get_object_or_404(Challenge, pk=self.kwargs["pk"])
        return self._challenge

    def test_func(self):
        challenge = self.get_challenge()
        user = self.request.user
        return (
            user.is_authenticated
            and user.organization is not None
            and challenge.publisher_id == user.organization_id
        )


class ChallengeEvaluationRoleRequiredMixin(ChallengePublisherRequiredMixin):
    required_role = None

    def test_func(self):
        if not super().test_func():
            return False
        return ChallengeEvaluationRoleAssignment.objects.filter(
            challenge=self.get_challenge(),
            user=self.request.user,
            role=self.required_role,
        ).exists()


class ChallengeEvaluationStartView(ChallengePublisherRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        challenge = self.get_challenge()

        try:
            start_challenge_evaluation(
                challenge=challenge,
                actor=request.user,
            )
        except ChallengeEvaluationValidationError as exc:
            for message in exc.messages:
                messages.error(request, message)
        else:
            messages.success(request, "El desafío pasó a estado En evaluación.")

        return HttpResponseRedirect(
            reverse("marketplace:challenge-detail", args=[challenge.pk])
        )


class ChallengeEvaluationRoleAssignmentUpdateView(ChallengePublisherRequiredMixin, FormView):
    form_class = ChallengeEvaluationRoleAssignmentForm
    template_name = "evaluation/challenge_evaluation_roles_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["challenge"] = self.get_challenge()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["challenge"] = self.get_challenge()
        return context

    def get_success_url(self):
        return reverse("marketplace:challenge-detail", args=[self.get_challenge().pk])

    def form_valid(self, form):
        try:
            assign_challenge_evaluation_roles(
                challenge=self.get_challenge(),
                actor=self.request.user,
                command=form.to_command(),
            )
        except ChallengeEvaluationValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(
            self.request,
            "El equipo de evaluación fue actualizado.",
        )
        return HttpResponseRedirect(self.get_success_url())


class AwardDecisionCreateView(ChallengeEvaluationRoleRequiredMixin, FormView):
    form_class = AwardDecisionForm
    template_name = "evaluation/award_decision_form.html"
    required_role = ChallengeEvaluationRoleAssignment.Role.ADJUDICATOR

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["challenge"] = self.get_challenge()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["challenge"] = self.get_challenge()
        form = context.get("form")
        if form is not None and hasattr(form, "evaluation_summaries"):
            context["application_evaluation_summaries"] = form.evaluation_summaries
            context["complete_application_evaluation_summaries"] = (
                form.complete_evaluation_summaries
            )
            context["pending_application_evaluation_summaries"] = (
                form.pending_evaluation_summaries
            )
            context["best_available_application_summaries"] = (
                form.best_available_summaries
            )
            context["award_blocking_messages"] = form.pending_award_messages
            context["is_award_blocked"] = form.is_award_blocked
        else:
            application_evaluation_summaries = (
                build_challenge_application_evaluation_summaries(
                    self.get_challenge(),
                    reveal_applicant_identity=False,
                )
            )
            context["application_evaluation_summaries"] = application_evaluation_summaries
            context["complete_application_evaluation_summaries"] = tuple(
                application
                for application in application_evaluation_summaries
                if application.evaluation_summary.is_complete
            )
            context["pending_application_evaluation_summaries"] = tuple(
                application
                for application in application_evaluation_summaries
                if not application.evaluation_summary.is_complete
            )
            context["best_available_application_summaries"] = tuple(
                application
                for application in application_evaluation_summaries
                if application.evaluation_summary.ranking_position == 1
            )
            context["award_blocking_messages"] = build_pending_award_messages(
                application_evaluation_summaries
            )
            context["is_award_blocked"] = bool(context["award_blocking_messages"])
        return context

    def get_success_url(self):
        return reverse("marketplace:challenge-detail", args=[self.get_challenge().pk])

    def form_valid(self, form):
        try:
            adjudicate_challenge(
                challenge=self.get_challenge(),
                actor=self.request.user,
                command=form.to_command(),
            )
        except ChallengeEvaluationValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(
            self.request,
            "La decisión de adjudicación fue registrada.",
        )
        return HttpResponseRedirect(self.get_success_url())


class ApplicationCriterionEvaluationUpdateView(
    ChallengeEvaluationRoleRequiredMixin,
    FormView,
):
    form_class = ApplicationCriterionEvaluationForm
    template_name = "evaluation/application_criterion_evaluation_form.html"
    required_role = ChallengeEvaluationRoleAssignment.Role.EVALUATOR

    def get_application(self):
        if not hasattr(self, "_application"):
            self._application = get_object_or_404(
                Application.objects.select_related("challenge"),
                pk=self.kwargs["application_pk"],
            )
        return self._application

    def dispatch(self, request, *args, **kwargs):
        if self.get_application().challenge_id != self.get_challenge().pk:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["challenge"] = self.get_challenge()
        kwargs["application"] = self.get_application()
        kwargs["evaluator"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["challenge"] = self.get_challenge()
        context["application"] = self.get_application()
        context["application_blind_reference"] = get_application_blind_reference(
            self.get_application()
        )
        return context

    def get_success_url(self):
        return reverse("marketplace:challenge-detail", args=[self.get_challenge().pk])

    def form_valid(self, form):
        try:
            evaluate_application_by_criteria(
                challenge=self.get_challenge(),
                application=self.get_application(),
                actor=self.request.user,
                command=form.to_command(),
            )
        except ChallengeEvaluationValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(
            self.request,
            "La evaluación por criterios fue registrada.",
        )
        return HttpResponseRedirect(self.get_success_url())
