from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "kind", "title", "created_at", "read_at")
    list_filter = ("kind", "created_at", "read_at")
    search_fields = ("recipient__username", "title", "body")
