from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from apps.identity.mixins import OperationalUserRequiredMixin
from apps.notifications.application.services import mark_all_notifications_as_read
from apps.notifications.models import Notification


class NotificationListView(OperationalUserRequiredMixin, ListView):
    model = Notification
    template_name = "notifications/notification_list.html"
    context_object_name = "notifications"
    paginate_by = 20
    operation_blocked_redirect_url = "home"

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


class NotificationMarkAllReadView(OperationalUserRequiredMixin, View):
    operation_blocked_redirect_url = "home"

    def post(self, request, *args, **kwargs):
        mark_all_notifications_as_read(recipient=request.user)
        return HttpResponseRedirect(reverse("notifications:list"))
