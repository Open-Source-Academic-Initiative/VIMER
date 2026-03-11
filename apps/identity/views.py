from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import FormView

from apps.identity.application.exceptions import DuplicateTaxIdError
from apps.identity.application.services import register_organization_user
from .forms import RegistrationForm

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

        return HttpResponseRedirect(self.get_success_url())
