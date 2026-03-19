from django.contrib import admin, messages
from django.contrib.admin.actions import delete_selected
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'organization', 'is_staff')
    list_filter = ('organization__role', 'is_staff', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ('Información de Organización', {'fields': ('organization',)}),
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
