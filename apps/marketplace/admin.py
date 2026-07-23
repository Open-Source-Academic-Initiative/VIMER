from django.contrib import admin
from .models import (
    Application,
    ApplicationAttachment,
    Challenge,
    ChallengeAttachment,
    ChallengeCategory,
    ChallengeEvaluationCriterion,
    ChallengeLifecycleEvent,
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
    list_display = (
        'title',
        'publisher',
        'status',
        'budget_amount',
        'budget_currency',
        'application_deadline',
        'created_at',
    )
    list_filter = ('status', 'categories', 'created_at')
    search_fields = ('title', 'description', 'evaluation_criteria')
    filter_horizontal = ('categories',)
    inlines = [ChallengeEvaluationCriterionInline]
    readonly_fields = ('status', 'created_at', 'updated_at')

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None and (
            obj.status != Challenge.Status.DRAFT or obj.applications.exists()
        ):
            readonly.extend(
                [
                    "publisher",
                    "title",
                    "description",
                    "evaluation_criteria",
                    "application_deadline",
                    "budget_amount",
                    "budget_currency",
                ]
            )
        return tuple(dict.fromkeys(readonly))

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return False
        return (
            obj.status == Challenge.Status.DRAFT
            and not obj.applications.exists()
            and not obj.lifecycle_events.exists()
        )

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'challenge',
        'applicant',
        'status',
        'offered_amount',
        'offer_currency',
        'applied_at',
        'updated_at',
    )
    list_filter = ('status', 'applied_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None and obj.status == Application.Status.SUBMITTED:
            readonly.extend(
                field.name
                for field in obj._meta.fields
                if field.name != "id"
            )
        return tuple(dict.fromkeys(readonly))

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return False
        return obj.status == Application.Status.DRAFT


@admin.register(ChallengeCategory)
class ChallengeCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'position')
    list_filter = ('is_active',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return False
        return not obj.challenges.exists()


@admin.register(ChallengeAttachment)
class ChallengeAttachmentAdmin(admin.ModelAdmin):
    list_display = ('challenge', 'original_filename', 'content_type', 'size', 'uploaded_by', 'created_at')
    search_fields = ('challenge__title', 'original_filename')
    readonly_fields = ('opaque_id', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return bool(obj and obj.challenge.status == Challenge.Status.DRAFT)


@admin.register(ApplicationAttachment)
class ApplicationAttachmentAdmin(admin.ModelAdmin):
    list_display = ('application', 'original_filename', 'content_type', 'size', 'uploaded_by', 'created_at')
    search_fields = ('application__challenge__title', 'application__applicant__business_name', 'original_filename')
    readonly_fields = ('opaque_id', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return bool(
            obj and obj.application.status == Application.Status.DRAFT
        )


@admin.register(ChallengeLifecycleEvent)
class ChallengeLifecycleEventAdmin(admin.ModelAdmin):
    list_display = (
        "challenge",
        "event_type",
        "from_status",
        "to_status",
        "actor",
        "occurred_at",
    )
    list_filter = ("event_type", "occurred_at")
    search_fields = ("challenge__title", "actor__username", "reason")
    readonly_fields = (
        "challenge",
        "event_type",
        "from_status",
        "to_status",
        "actor",
        "reason",
        "occurred_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
