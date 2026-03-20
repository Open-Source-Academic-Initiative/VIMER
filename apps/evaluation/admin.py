from django.contrib import admin

from apps.evaluation.models import AwardDecision


@admin.register(AwardDecision)
class AwardDecisionAdmin(admin.ModelAdmin):
    list_display = ("challenge", "winning_application", "decided_by", "decided_at")
    list_filter = ("decided_at",)
    search_fields = ("challenge__title", "comment", "winning_application__applicant__business_name")
