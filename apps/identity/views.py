from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from apps.identity.application.exceptions import (
    DuplicateEmailError,
    DuplicateTaxIdError,
    DuplicateUsernameError,
    RegistrationValidationError,
)
from apps.identity.application.services import register_organization_user
from .forms import RegistrationForm


class LandingPageView(TemplateView):
    template_name = "landing.html"


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
