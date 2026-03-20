from django.contrib import admin

from apps.evaluation.models import (
    ApplicationCriterionEvaluation,
    AwardDecision,
    ChallengeTimelineEntry,
)


@admin.register(AwardDecision)
class AwardDecisionAdmin(admin.ModelAdmin):
    list_display = ("challenge", "winning_application", "decided_by", "decided_at")
    list_filter = ("decided_at",)
    search_fields = ("challenge__title", "comment", "winning_application__applicant__business_name")


@admin.register(ChallengeTimelineEntry)
class ChallengeTimelineEntryAdmin(admin.ModelAdmin):
    list_display = ("challenge", "event_type", "actor", "occurred_at")
    list_filter = ("event_type", "occurred_at")
    search_fields = ("challenge__title", "description", "actor__username")


@admin.register(ApplicationCriterionEvaluation)
class ApplicationCriterionEvaluationAdmin(admin.ModelAdmin):
    list_display = ("application", "criterion", "score", "evaluated_by", "evaluated_at")
    list_filter = ("score", "evaluated_at")
    search_fields = (
        "application__challenge__title",
        "application__applicant__business_name",
        "criterion__label",
        "comment",
    )
