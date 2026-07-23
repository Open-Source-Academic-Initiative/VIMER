from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect


class OperationalUserRequiredMixin(LoginRequiredMixin):
    """Require an authenticated user that can operate the platform.

    ``User.can_operate`` is true only for native-active, approved representatives
    with a verified email and an organization membership (see
    :mod:`apps.identity.models`). Apply this mixin to every private read and
    write boundary. Unauthenticated users still fall through to
    ``LoginRequiredMixin`` and get redirected to login.
    """

    operation_blocked_redirect_url = "marketplace:challenge-list"
    operation_blocked_message = (
        "Debes verificar tu correo electrónico y tener una cuenta activa "
        "para realizar esta acción."
    )

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated and not user.can_operate:
            messages.error(request, self.operation_blocked_message)
            return redirect(self.operation_blocked_redirect_url)
        return super().dispatch(request, *args, **kwargs)
