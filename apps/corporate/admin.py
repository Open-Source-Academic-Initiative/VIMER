from django.contrib import admin
from .models import Organization

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'tax_id', 'role', 'contact_email')
    list_filter = ('role',)
    search_fields = ('business_name', 'tax_id')
    ordering = ('business_name',)
