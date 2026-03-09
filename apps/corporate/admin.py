from django.contrib import admin
from .models import Organization

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'nit', 'role', 'contact_email')
    list_filter = ('role',)
    search_fields = ('business_name', 'nit')
    ordering = ('business_name',)
