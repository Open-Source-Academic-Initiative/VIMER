from django import forms
from django.db import transaction
from .models import User
from apps.corporate.models import Organization

class RegistrationForm(forms.ModelForm):
    # Campos de Organización
    nit = forms.CharField(max_length=20, label="NIT de la Organización")
    business_name = forms.CharField(max_length=255, label="Razón Social")
    chamber_of_commerce = forms.CharField(max_length=100, label="Registro Cámara de Comercio")
    role = forms.ChoiceField(choices=Organization.MarketRole.choices, label="Rol en la Plataforma")
    
    # Campos de Usuario
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirmar Contraseña")

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data

    @transaction.atomic
    def save(self):
        # 1. Crear Organización
        org = Organization.objects.create(
            nit=self.cleaned_data['nit'],
            business_name=self.cleaned_data['business_name'],
            chamber_of_commerce_record=self.cleaned_data['chamber_of_commerce'],
            role=self.cleaned_data['role'],
            contact_email=self.cleaned_data['email'] # Default inicial
        )
        # 2. Crear Usuario
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.organization = org
        user.save()
        return user
