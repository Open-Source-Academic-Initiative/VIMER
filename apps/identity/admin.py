from django.contrib import admin, messages
from django.contrib.admin.actions import delete_selected
from django.contrib.auth.admin import UserAdmin
from .models import EmailVerificationToken, OrganizationJoinRequest, User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username',
        'email',
        'organization',
        'status',
        'is_organization_titular',
        'is_email_verified',
        'is_staff',
    )
    list_filter = (
        'organization__role',
        'status',
        'is_organization_titular',
        'is_email_verified',
        'is_staff',
        'is_superuser',
    )
    fieldsets = UserAdmin.fieldsets + (
        (
            'Información de Organización',
            {
                'fields': (
                    'organization',
                    'status',
                    'is_organization_titular',
                    'is_email_verified',
                    'accepted_terms_version',
                    'accepted_privacy_policy_version',
                )
            },
        ),
    )
    actions = ('delete_selected_preserving_self',)

    @admin.action(
        permissions=['delete'],
        description='Eliminar usuarios seleccionados',
    )
    def delete_selected_preserving_self(self, request, queryset):
        if request.user.is_superuser and queryset.filter(pk=request.user.pk).exists():
            queryset = queryset.exclude(pk=request.user.pk)
            self.message_user(
                request,
                'No puedes eliminarte a ti mismo desde el panel de administración.',
                level=messages.WARNING,
            )

        if not queryset.exists():
            return None

        return delete_selected(self, request, queryset)

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions

    def has_delete_permission(self, request, obj=None):
        if (
            obj is not None
            and request.user.is_superuser
            and obj.pk == request.user.pk
        ):
            return False
        return super().has_delete_permission(request, obj=obj)


@admin.register(OrganizationJoinRequest)
class OrganizationJoinRequestAdmin(admin.ModelAdmin):
    list_display = (
        'organization',
        'requester',
        'status',
        'decided_by',
        'expires_at',
        'created_at',
    )
    list_filter = ('status', 'organization__role')
    search_fields = (
        'organization__business_name',
        'requester__username',
        'requester__email',
    )
    readonly_fields = ('created_at',)


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'expires_at', 'used_at', 'created_at')
    search_fields = ('user__username', 'user__email', 'token')
    readonly_fields = ('token', 'created_at')
