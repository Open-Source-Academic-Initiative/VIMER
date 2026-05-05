from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import FormView, ListView, TemplateView

from apps.identity.application.exceptions import (
    DuplicateEmailError,
    DuplicateTaxIdError,
    DuplicateUsernameError,
    OrganizationJoinRequestError,
    OrganizationTitularityTransferError,
    RegistrationValidationError,
)
from apps.identity.application.commands import (
    DecideOrganizationJoinRequestCommand,
    TransferOrganizationTitularityCommand,
)
from apps.identity.application.services import (
    approve_organization_join_request,
    register_organization_user,
    reject_organization_join_request,
    transfer_organization_titularity,
)
from apps.identity.models import EmailVerificationToken, OrganizationJoinRequest, User
from .forms import RegistrationForm


class LandingPageView(TemplateView):
    template_name = "landing.html"


class TermsPageView(TemplateView):
    template_name = "legal/terms.html"


class PrivacyPolicyPageView(TemplateView):
    template_name = "legal/privacy_policy.html"


class FAQPageView(TemplateView):
    template_name = "help/faq.html"


class SignUpView(FormView):
    form_class = RegistrationForm
    template_name = "identity/signup.html"
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        try:
            register_organization_user(form.to_command())
        except DuplicateTaxIdError:
            form.add_error("tax_id", "Ya existe una organización registrada con este NIT.")
            return self.form_invalid(form)
        except DuplicateUsernameError:
            form.add_error("username", "Ya existe un usuario registrado con este nombre de usuario.")
            return self.form_invalid(form)
        except DuplicateEmailError:
            form.add_error("email", "Ya existe un usuario registrado con este correo electrónico.")
            return self.form_invalid(form)
        except RegistrationValidationError as exc:
            field_aliases = {
                "contact_email": "email",
                "chamber_of_commerce_record": "chamber_of_commerce",
            }
            if exc.message_dict:
                for field, messages in exc.message_dict.items():
                    if field == "__all__":
                        target_field = None
                    else:
                        target_field = field_aliases.get(field, field)
                        if target_field not in form.fields:
                            target_field = None
                    for message in messages:
                        form.add_error(target_field, message)
            else:
                for message in exc.messages:
                    form.add_error(None, message)
            return self.form_invalid(form)

        return HttpResponseRedirect(self.get_success_url())


class EmailVerificationView(TemplateView):
    template_name = "identity/email_verified.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        token = EmailVerificationToken.objects.filter(
            token=self.kwargs["token"]
        ).select_related("user").first()
        if token is None:
            context["verified"] = False
            context["message"] = "El enlace de verificación no es válido."
        elif not token.is_usable:
            context["verified"] = False
            context["message"] = "El enlace de verificación expiró o ya fue usado."
        else:
            token.mark_used()
            context["verified"] = True
            context["message"] = "Tu correo fue verificado correctamente."
        return context


class TitularRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return (
            user.is_authenticated
            and user.organization_id is not None
            and user.status == User.AccountStatus.ACTIVE
            and user.is_organization_titular
        )


class OrganizationJoinRequestListView(TitularRequiredMixin, ListView):
    model = OrganizationJoinRequest
    template_name = "identity/join_request_list.html"
    context_object_name = "join_requests"

    def get_queryset(self):
        return OrganizationJoinRequest.objects.filter(
            organization_id=self.request.user.organization_id,
            status=OrganizationJoinRequest.Status.PENDING,
        ).select_related("requester", "organization")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_members"] = User.objects.filter(
            organization_id=self.request.user.organization_id,
            status=User.AccountStatus.ACTIVE,
        ).exclude(pk=self.request.user.pk)
        return context


class OrganizationJoinRequestApproveView(TitularRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            approve_organization_join_request(
                actor=request.user,
                command=DecideOrganizationJoinRequestCommand(
                    join_request_id=kwargs["pk"],
                ),
            )
            messages.success(request, "La solicitud fue aprobada.")
        except OrganizationJoinRequestError as exc:
            for message in exc.messages:
                messages.error(request, message)
        return HttpResponseRedirect(reverse("organization-join-requests"))


class OrganizationJoinRequestRejectView(TitularRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            reject_organization_join_request(
                actor=request.user,
                command=DecideOrganizationJoinRequestCommand(
                    join_request_id=kwargs["pk"],
                ),
            )
            messages.success(request, "La solicitud fue rechazada.")
        except OrganizationJoinRequestError as exc:
            for message in exc.messages:
                messages.error(request, message)
        return HttpResponseRedirect(reverse("organization-join-requests"))


class OrganizationTitularityTransferView(TitularRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            transfer_organization_titularity(
                actor=request.user,
                command=TransferOrganizationTitularityCommand(
                    target_user_id=int(request.POST.get("target_user_id", "0")),
                ),
            )
            messages.success(request, "La titularidad fue transferida.")
        except (ValueError, OrganizationTitularityTransferError) as exc:
            if isinstance(exc, ValueError):
                messages.error(request, "Selecciona un representante válido.")
            else:
                for message in exc.messages:
                    messages.error(request, message)
        return HttpResponseRedirect(reverse("organization-join-requests"))
