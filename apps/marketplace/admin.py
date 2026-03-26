from django.contrib import admin
from .models import Application, Challenge, ChallengeEvaluationCriterion


class ChallengeEvaluationCriterionInline(admin.TabularInline):
    model = ChallengeEvaluationCriterion
    extra = 0
    can_delete = False
    fields = ("position", "label")
    readonly_fields = ("position", "label")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ('title', 'publisher', 'status', 'application_deadline', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'description', 'evaluation_criteria')
    inlines = [ChallengeEvaluationCriterionInline]

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('challenge', 'applicant', 'applied_at')
    list_filter = ('applied_at',)
