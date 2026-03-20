from django.contrib import admin
from .models import Application, Challenge, ChallengeEvaluationCriterion


class ChallengeEvaluationCriterionInline(admin.TabularInline):
    model = ChallengeEvaluationCriterion
    extra = 0

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
