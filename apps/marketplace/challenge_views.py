from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db import models
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from apps.corporate.models import Organization
from apps.identity.mixins import OperationalUserRequiredMixin
from apps.evaluation.application.queries import (
    build_challenge_publisher_detail_read_model,
)
from apps.marketplace.application.exceptions import (
    ChallengeLifecycleValidationError,
    ChallengePublicationValidationError,
)
from apps.marketplace.application.services import (
    cancel_challenge,
    close_challenge,
    create_challenge_draft,
    declare_challenge_deserted,
    publish_challenge,
    publish_challenge_draft,
    update_challenge_draft,
)
from apps.marketplace.challenge_forms import (
    ChallengePublicationForm,
    ChallengeTransitionForm,
)
from apps.marketplace.models import Application, Challenge, ChallengeCategory


class RoleRequiredMixin(UserPassesTestMixin):
    role_required = None

    def test_func(self):
        return (
            self.request.user.is_authenticated
            and self.request.user.can_operate
            and self.request.user.organization is not None
            and self.request.user.organization.role == self.role_required
        )


class ChallengeListView(ListView):
    model = Challenge
    template_name = "marketplace/challenge_list.html"
    context_object_name = "challenges"
    paginate_by = 10

    def get_queryset(self):
        organization = (
            self.request.user.organization
            if (
                self.request.user.is_authenticated
                and getattr(self.request.user, "can_operate", False)
            )
            else None
        )
        queryset = (
            Challenge.objects.visible_to_organization(organization)
            .select_related("publisher")
            .prefetch_related("categories")
        )
        query = (self.request.GET.get("q") or "").strip()
        category = (self.request.GET.get("category") or "").strip()
        status = (self.request.GET.get("status") or "").strip()
        if query:
            queryset = queryset.filter(
                models.Q(title__icontains=query)
                | models.Q(description__icontains=query)
            )
        if category:
            queryset = queryset.filter(categories__slug=category)
        if status:
            queryset = queryset.filter(status=status)
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = ChallengeCategory.objects.filter(is_active=True)
        context["selected_category"] = self.request.GET.get("category", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["query"] = self.request.GET.get("q", "")
        context["status_choices"] = Challenge.Status.choices
        filter_params = self.request.GET.copy()
        filter_params.pop("page", None)
        context["extra_query"] = filter_params.urlencode()
        return context


class ChallengeDetailView(DetailView):
    model = Challenge
    template_name = "marketplace/challenge_detail.html"
    context_object_name = "challenge"

    def get_queryset(self):
        organization = (
            self.request.user.organization
            if (
                self.request.user.is_authenticated
                and getattr(self.request.user, "can_operate", False)
            )
            else None
        )
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
        context["submitted_application_count"] = (
            detail_read_model.submitted_application_count
        )
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
        context["pending_award_applications"] = list(
            detail_read_model.pending_award_applications
        )
        context["best_available_applications"] = list(
            detail_read_model.best_available_applications
        )
        context["award_blocking_messages"] = list(
            detail_read_model.award_blocking_messages
        )
        requester_application = None
        if (
            self.request.user.is_authenticated
            and self.request.user.is_operational_member_of(
                self.request.user.organization_id
            )
        ):
            requester_application = Application.objects.filter(
                challenge=challenge,
                applicant_id=self.request.user.organization_id,
            ).first()
        context["requester_application"] = requester_application
        is_operational_publisher = (
            self.request.user.is_authenticated
            and self.request.user.is_operational_member_of(
                challenge.publisher_id
            )
        )
        context["is_challenge_publisher"] = is_operational_publisher
        context["lifecycle_events"] = (
            challenge.lifecycle_events.select_related("actor")
            if is_operational_publisher
            else ()
        )
        context["can_publish_challenge"] = (
            is_operational_publisher
            and challenge.status == Challenge.Status.DRAFT
        )
        context["can_edit_challenge"] = context["can_publish_challenge"]
        context["can_close_challenge"] = (
            is_operational_publisher
            and challenge.status == Challenge.Status.PUBLISHED
        )
        context["can_cancel_challenge"] = (
            is_operational_publisher
            and challenge.status
            in {
                Challenge.Status.DRAFT,
                Challenge.Status.PUBLISHED,
                Challenge.Status.CLOSED,
            }
        )
        context["can_declare_deserted"] = (
            is_operational_publisher
            and challenge.status
            in {
                Challenge.Status.CLOSED,
                Challenge.Status.UNDER_EVALUATION,
            }
            and detail_read_model.award_decision is None
        )
        return context


class ChallengeCreateView(OperationalUserRequiredMixin, RoleRequiredMixin, FormView):
    form_class = ChallengePublicationForm
    role_required = Organization.MarketRole.DEMAND_SIDE
    template_name = "marketplace/challenge_form.html"
    success_url = reverse_lazy("marketplace:challenge-list")

    def form_valid(self, form):
        try:
            if self.request.POST.get("intent") == "draft":
                create_challenge_draft(
                    publisher=self.request.user.organization,
                    command=form.to_command(),
                    actor=self.request.user,
                )
                messages.success(self.request, "El borrador del desafío fue guardado.")
            else:
                publish_challenge(
                    publisher=self.request.user.organization,
                    command=form.to_command(),
                    actor=self.request.user,
                )
                messages.success(self.request, "El desafío fue publicado.")
        except (
            ChallengePublicationValidationError,
            ChallengeLifecycleValidationError,
        ) as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)
        return HttpResponseRedirect(self.get_success_url())


class PublisherChallengeRequiredMixin(
    OperationalUserRequiredMixin,
    UserPassesTestMixin,
):
    def get_challenge(self):
        if not hasattr(self, "_challenge"):
            self._challenge = get_object_or_404(
                Challenge.objects.select_related("publisher"),
                pk=self.kwargs["pk"],
            )
        return self._challenge

    def test_func(self):
        return self.request.user.is_operational_member_of(
            self.get_challenge().publisher_id
        )


class ChallengeDraftUpdateView(PublisherChallengeRequiredMixin, FormView):
    form_class = ChallengePublicationForm
    template_name = "marketplace/challenge_form.html"

    def dispatch(self, request, *args, **kwargs):
        if self.get_challenge().status != Challenge.Status.DRAFT:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        challenge = self.get_challenge()
        return {
            "title": challenge.title,
            "description": challenge.description,
            "evaluation_criteria": challenge.evaluation_criteria,
            "application_deadline": challenge.application_deadline,
            "budget_amount": challenge.budget_amount,
            "budget_currency": challenge.budget_currency,
            "categories": challenge.categories.all(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["challenge"] = self.get_challenge()
        context["is_editing_draft"] = True
        return context

    def get_success_url(self):
        return reverse(
            "marketplace:challenge-detail",
            args=[self.get_challenge().pk],
        )

    def form_valid(self, form):
        try:
            challenge = update_challenge_draft(
                challenge=self.get_challenge(),
                command=form.to_command(),
                actor=self.request.user,
            )
            if self.request.POST.get("intent") == "publish":
                publish_challenge_draft(
                    challenge=challenge,
                    actor=self.request.user,
                )
                messages.success(self.request, "El desafío fue actualizado y publicado.")
            else:
                messages.success(self.request, "El borrador fue actualizado.")
        except (
            ChallengePublicationValidationError,
            ChallengeLifecycleValidationError,
        ) as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)
        return HttpResponseRedirect(self.get_success_url())


class ChallengeTransitionView(PublisherChallengeRequiredMixin, FormView):
    form_class = ChallengeTransitionForm
    template_name = "marketplace/challenge_transition_form.html"
    action_label = ""
    reason_required = False
    reason_help_text = ""
    success_message = ""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["reason_required"] = self.reason_required
        kwargs["reason_help_text"] = self.reason_help_text
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["challenge"] = self.get_challenge()
        context["action_label"] = self.action_label
        return context

    def get_success_url(self):
        return reverse(
            "marketplace:challenge-detail",
            args=[self.get_challenge().pk],
        )

    def perform_transition(self, *, challenge, actor, reason):
        raise NotImplementedError

    def form_valid(self, form):
        try:
            self.perform_transition(
                challenge=self.get_challenge(),
                actor=self.request.user,
                reason=form.cleaned_data.get("reason", ""),
            )
        except ChallengeLifecycleValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)
        messages.success(self.request, self.success_message)
        return HttpResponseRedirect(self.get_success_url())


class ChallengePublishView(ChallengeTransitionView):
    action_label = "Publicar desafío"
    success_message = "El desafío fue publicado."

    def perform_transition(self, *, challenge, actor, reason):
        return publish_challenge_draft(challenge=challenge, actor=actor)


class ChallengeCloseView(ChallengeTransitionView):
    action_label = "Cerrar recepción de propuestas"
    reason_help_text = (
        "Es obligatorio si cierras antes de que termine la fecha límite."
    )
    success_message = "La recepción de propuestas fue cerrada."

    def perform_transition(self, *, challenge, actor, reason):
        return close_challenge(challenge=challenge, actor=actor, reason=reason)


class ChallengeCancelView(ChallengeTransitionView):
    action_label = "Cancelar desafío"
    reason_required = True
    reason_help_text = "Explica por qué se cancela el proceso."
    success_message = "El desafío fue cancelado."

    def perform_transition(self, *, challenge, actor, reason):
        return cancel_challenge(
            challenge=challenge,
            actor=actor,
            reason=reason,
        )


class ChallengeDesertView(ChallengeTransitionView):
    action_label = "Declarar desafío desierto"
    reason_required = True
    reason_help_text = "Registra la justificación formal de la decisión."
    success_message = "El desafío fue declarado desierto."

    def perform_transition(self, *, challenge, actor, reason):
        return declare_challenge_deserted(
            challenge=challenge,
            actor=actor,
            reason=reason,
        )


class MyChallengesView(
    OperationalUserRequiredMixin,
    RoleRequiredMixin,
    ListView,
):
    model = Challenge
    template_name = "marketplace/my_challenges.html"
    context_object_name = "challenges"
    role_required = Organization.MarketRole.DEMAND_SIDE
    paginate_by = 20

    def get_queryset(self):
        return (
            Challenge.objects.filter(publisher=self.request.user.organization)
            .prefetch_related("categories")
            .order_by("-updated_at")
        )


class MyApplicationsView(
    OperationalUserRequiredMixin,
    RoleRequiredMixin,
    ListView,
):
    model = Application
    template_name = "marketplace/my_applications.html"
    context_object_name = "applications"
    role_required = Organization.MarketRole.SUPPLY_SIDE
    paginate_by = 20

    def get_queryset(self):
        return (
            Application.objects.filter(applicant=self.request.user.organization)
            .select_related("challenge", "challenge__publisher")
            .order_by("-updated_at")
        )
