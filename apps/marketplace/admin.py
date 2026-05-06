from django.contrib import admin
from .models import (
    Application,
    ApplicationAttachment,
    Challenge,
    ChallengeAttachment,
    ChallengeCategory,
    ChallengeEvaluationCriterion,
)


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
    list_filter = ('status', 'categories', 'created_at')
    search_fields = ('title', 'description', 'evaluation_criteria')
    filter_horizontal = ('categories',)
    inlines = [ChallengeEvaluationCriterionInline]

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('challenge', 'applicant', 'status', 'applied_at', 'updated_at')
    list_filter = ('status', 'applied_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ChallengeCategory)
class ChallengeCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'position')
    list_filter = ('is_active',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')


@admin.register(ChallengeAttachment)
class ChallengeAttachmentAdmin(admin.ModelAdmin):
    list_display = ('challenge', 'original_filename', 'content_type', 'size', 'uploaded_by', 'created_at')
    search_fields = ('challenge__title', 'original_filename')
    readonly_fields = ('opaque_id', 'created_at')


@admin.register(ApplicationAttachment)
class ApplicationAttachmentAdmin(admin.ModelAdmin):
    list_display = ('application', 'original_filename', 'content_type', 'size', 'uploaded_by', 'created_at')
    search_fields = ('application__challenge__title', 'application__applicant__business_name', 'original_filename')
    readonly_fields = ('opaque_id', 'created_at')
