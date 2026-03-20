from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import FormView

from apps.evaluation.application.exceptions import ChallengeEvaluationValidationError
from apps.evaluation.application.services import (
    adjudicate_challenge,
    start_challenge_evaluation,
)
from apps.evaluation.forms import AwardDecisionForm
from apps.marketplace.models import Challenge


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


class AwardDecisionCreateView(ChallengePublisherRequiredMixin, FormView):
    form_class = AwardDecisionForm
    template_name = "evaluation/award_decision_form.html"

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
