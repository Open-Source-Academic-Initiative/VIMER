from django import forms
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from apps.corporate.avatar_utils import validate_logo_image
from .models import User
from apps.corporate.models import Organization
from apps.identity.application.commands import RegisterOrganizationUserCommand

class RegistrationForm(forms.Form):
    # Organization fields
    tax_id = forms.CharField(max_length=20, label="NIT de la Organización")
    business_name = forms.CharField(max_length=255, label="Razón Social")
    chamber_of_commerce = forms.CharField(max_length=100, label="Registro Cámara de Comercio")
    role = forms.ChoiceField(choices=Organization.MarketRole.choices, label="Rol en la Plataforma")
    contact_phone = forms.CharField(max_length=20, label="Teléfono de Contacto")
    logo = forms.ImageField(
        required=False,
        label="Logo de la organización (PNG o JPG)",
    )
    accept_terms = forms.BooleanField(
        label="Acepto los Términos y Condiciones",
        required=True,
    )
    accept_privacy_policy = forms.BooleanField(
        label="Acepto la Política de Tratamiento de Datos Personales",
        required=True,
    )
    turnstile_token = forms.CharField(
        required=False,
        widget=forms.HiddenInput,
    )
    
    # User fields
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirmar Contraseña")

    username = forms.CharField(max_length=150, label="Nombre de usuario")
    email = forms.EmailField(label="Correo electrónico")
    first_name = forms.CharField(max_length=150, label="Nombre")
    last_name = forms.CharField(max_length=150, label="Apellido")

    def clean_tax_id(self):
        tax_id = self.cleaned_data["tax_id"].strip()
        return tax_id

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ya existe un usuario registrado con este nombre de usuario.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe un usuario registrado con este correo electrónico.")
        return email

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if not logo:
            return None

        try:
            validate_logo_image(logo)
        except ValidationError as exc:
            raise forms.ValidationError(exc.messages)
        return logo

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

        turnstile_response = (
            cleaned_data.get("turnstile_token")
            or self.data.get("cf-turnstile-response", "")
        )
        cleaned_data["turnstile_token"] = turnstile_response
        if settings.TURNSTILE_SITE_KEY and not turnstile_response:
            self.add_error(None, "Debes completar la verificación anti-spam.")

        return cleaned_data

    def to_command(self) -> RegisterOrganizationUserCommand:
        return RegisterOrganizationUserCommand(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            password=self.cleaned_data["password"],
            tax_id=self.cleaned_data["tax_id"],
            business_name=self.cleaned_data["business_name"],
            chamber_of_commerce_record=self.cleaned_data["chamber_of_commerce"],
            role=self.cleaned_data["role"],
            contact_phone=self.cleaned_data["contact_phone"],
            logo_upload=self.cleaned_data.get("logo"),
            accepted_terms=self.cleaned_data["accept_terms"],
            accepted_privacy_policy=self.cleaned_data["accept_privacy_policy"],
            turnstile_token=self.cleaned_data.get("turnstile_token", ""),
        )
