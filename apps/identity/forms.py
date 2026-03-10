from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction
from .models import User
from apps.corporate.models import Organization

class RegistrationForm(forms.ModelForm):
    # Organization fields
    tax_id = forms.CharField(max_length=20, label="NIT de la Organización")
    business_name = forms.CharField(max_length=255, label="Razón Social")
    chamber_of_commerce = forms.CharField(max_length=100, label="Registro Cámara de Comercio")
    role = forms.ChoiceField(choices=Organization.MarketRole.choices, label="Rol en la Plataforma")
    contact_phone = forms.CharField(max_length=20, label="Teléfono de Contacto")
    
    # User fields
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirmar Contraseña")

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

    def clean_tax_id(self):
        tax_id = self.cleaned_data["tax_id"].strip()
        if Organization.objects.filter(tax_id=tax_id).exists():
            raise forms.ValidationError("Ya existe una organización registrada con este NIT.")
        return tax_id

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            raise forms.ValidationError("Las contraseñas no coinciden.")

        if password:
            candidate_user = User(
                username=cleaned_data.get("username", ""),
                email=cleaned_data.get("email", ""),
                first_name=cleaned_data.get("first_name", ""),
                last_name=cleaned_data.get("last_name", ""),
            )
            try:
                validate_password(password, user=candidate_user)
            except ValidationError as exc:
                self.add_error("password", exc)

        return cleaned_data

    @transaction.atomic
    def save(self):
        try:
            # 1. Create organization
            organization = Organization.objects.create(
                tax_id=self.cleaned_data['tax_id'],
                business_name=self.cleaned_data['business_name'],
                chamber_of_commerce_record=self.cleaned_data['chamber_of_commerce'],
                role=self.cleaned_data['role'],
                contact_email=self.cleaned_data['email'],
                contact_phone=self.cleaned_data['contact_phone'],
            )
        except IntegrityError as exc:
            raise forms.ValidationError(
                {"tax_id": "Ya existe una organización registrada con este NIT."}
            ) from exc

        # 2. Create user
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.organization = organization
        user.save()
        return user
