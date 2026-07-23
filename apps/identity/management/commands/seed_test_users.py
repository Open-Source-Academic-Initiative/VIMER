from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.corporate.avatar_utils import generate_default_logo
from apps.corporate.models import Organization
from apps.identity.models import OrganizationJoinRequest

# Single shared password for every seeded QA account.
QA_PASSWORD = "QaVimer2026!"

# key -> organization definition
ORGANIZATIONS = {
    "sol": {
        "tax_id": "901000001",
        "business_name": "Soluciones Andinas S.A.S.",
        "chamber_of_commerce_record": "CC-SOL-0001",
        "role": Organization.MarketRole.DEMAND_SIDE,
        "contact_email": "contacto@solucionesandinas.test",
        "contact_phone": "6011000001",
    },
    "prov1": {
        "tax_id": "901000002",
        "business_name": "Innovatech Proveedores S.A.S.",
        "chamber_of_commerce_record": "CC-PRV-0002",
        "role": Organization.MarketRole.SUPPLY_SIDE,
        "contact_email": "contacto@innovatech.test",
        "contact_phone": "6011000002",
    },
    "prov2": {
        "tax_id": "901000003",
        "business_name": "DataSoluciones Ltda.",
        "chamber_of_commerce_record": "CC-PRV-0003",
        "role": Organization.MarketRole.SUPPLY_SIDE,
        "contact_email": "contacto@datasoluciones.test",
        "contact_phone": "6011000003",
    },
    "nover": {
        "tax_id": "901000004",
        "business_name": "Entidad Sin Verificar S.A.S.",
        "chamber_of_commerce_record": "CC-NOV-0004",
        "role": Organization.MarketRole.DEMAND_SIDE,
        "contact_email": "contacto@sinverificar.test",
        "contact_phone": "6011000004",
    },
}

User = get_user_model()
_ACTIVE = User.AccountStatus.ACTIVE
_PENDING = User.AccountStatus.PENDING_APPROVAL

# Each tuple drives one QA account and documents the flow it unlocks.
USERS = [
    {
        "username": "qa_admin",
        "email": "qa.admin@vimer.test",
        "first_name": "QA",
        "last_name": "Administrador",
        "org": None,
        "superuser": True,
        "titular": False,
        "verified": True,
        "status": _ACTIVE,
        "purpose": "Superusuario de plataforma: /admin/ y /admin/dashboard/.",
    },
    {
        "username": "qa_sol_titular",
        "email": "qa.sol.titular@vimer.test",
        "first_name": "Tatiana",
        "last_name": "Solís",
        "org": "sol",
        "titular": True,
        "verified": True,
        "status": _ACTIVE,
        "purpose": "Titular Solicitante: publica desafíos, define equipo de evaluación, inicia evaluación.",
    },
    {
        "username": "qa_evaluador_a",
        "email": "qa.evaluador.a@vimer.test",
        "first_name": "Esteban",
        "last_name": "Vargas",
        "org": "sol",
        "titular": False,
        "verified": True,
        "status": _ACTIVE,
        "purpose": "Miembro del Solicitante: asignar como Evaluador designado (evalúa por criterio).",
    },
    {
        "username": "qa_evaluador_b",
        "email": "qa.evaluador.b@vimer.test",
        "first_name": "Bianca",
        "last_name": "Rojas",
        "org": "sol",
        "titular": False,
        "verified": True,
        "status": _ACTIVE,
        "purpose": "Segundo Evaluador designado: prueba múltiples evaluadores por criterio.",
    },
    {
        "username": "qa_adjudicador",
        "email": "qa.adjudicador@vimer.test",
        "first_name": "Adriana",
        "last_name": "Duque",
        "org": "sol",
        "titular": False,
        "verified": True,
        "status": _ACTIVE,
        "purpose": "Adjudicador designado: registra la adjudicación (incluye empate/excepcional).",
    },
    {
        "username": "qa_observador",
        "email": "qa.observador@vimer.test",
        "first_name": "Oscar",
        "last_name": "Bernal",
        "org": "sol",
        "titular": False,
        "verified": True,
        "status": _ACTIVE,
        "purpose": "Observador del equipo de evaluación (sin permiso de evaluar ni adjudicar).",
    },
    {
        "username": "qa_pendiente",
        "email": "qa.pendiente@vimer.test",
        "first_name": "Pedro",
        "last_name": "Niño",
        "org": "sol",
        "titular": False,
        "verified": False,
        "status": _PENDING,
        "join_request": True,
        "purpose": "Solicitud de unión PENDIENTE: el titular la aprueba/rechaza; también prueba el gating.",
    },
    {
        "username": "qa_prov1_titular",
        "email": "qa.prov1.titular@vimer.test",
        "first_name": "Iván",
        "last_name": "Mejía",
        "org": "prov1",
        "titular": True,
        "verified": True,
        "status": _ACTIVE,
        "purpose": "Titular Proveedor 1: guarda borrador y envía propuesta (adjuntos/markdown).",
    },
    {
        "username": "qa_prov2_titular",
        "email": "qa.prov2.titular@vimer.test",
        "first_name": "Diana",
        "last_name": "Castro",
        "org": "prov2",
        "titular": True,
        "verified": True,
        "status": _ACTIVE,
        "purpose": "Titular Proveedor 2: segunda propuesta para ranking comparativo y evaluación ciega.",
    },
    {
        "username": "qa_no_verificado",
        "email": "qa.no.verificado@vimer.test",
        "first_name": "Noé",
        "last_name": "Vera",
        "org": "nover",
        "titular": True,
        "verified": False,
        "status": _ACTIVE,
        "purpose": "Cuenta con correo NO verificado: confirma el gating (no puede publicar/postular/evaluar).",
    },
]


class Command(BaseCommand):
    help = (
        "Seed a complete, idempotent set of QA test users covering every role and "
        "account state, so the QA team can exercise all flows manually."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        organizations = self._seed_organizations()
        rows = self._seed_users(organizations)
        self._print_summary(rows)

    def _seed_organizations(self) -> dict[str, Organization]:
        organizations = {}
        for key, data in ORGANIZATIONS.items():
            organization, _ = Organization.objects.get_or_create(
                tax_id=data["tax_id"],
                defaults={
                    "business_name": data["business_name"],
                    "chamber_of_commerce_record": data["chamber_of_commerce_record"],
                    "role": data["role"],
                    "contact_email": data["contact_email"],
                    "contact_phone": data["contact_phone"],
                },
            )
            organization.business_name = data["business_name"]
            organization.chamber_of_commerce_record = data["chamber_of_commerce_record"]
            organization.role = data["role"]
            organization.contact_email = data["contact_email"]
            organization.contact_phone = data["contact_phone"]
            if not organization.logo:
                organization.logo = generate_default_logo(
                    business_name=organization.business_name,
                    tax_id=organization.tax_id,
                )
            organization.save()
            organizations[key] = organization
        return organizations

    def _seed_users(self, organizations: dict[str, Organization]) -> list[tuple]:
        rows = []
        for definition in USERS:
            organization = (
                organizations[definition["org"]] if definition["org"] else None
            )
            user, _ = User.objects.get_or_create(
                username=definition["username"],
                defaults={"email": definition["email"]},
            )
            user.email = definition["email"]
            user.first_name = definition["first_name"]
            user.last_name = definition["last_name"]
            user.organization = organization
            user.is_organization_titular = definition["titular"]
            user.is_email_verified = definition["verified"]
            user.status = definition["status"]
            user.is_staff = definition.get("superuser", False)
            user.is_superuser = definition.get("superuser", False)
            user.accepted_terms_version = settings.LEGAL_TERMS_VERSION
            user.accepted_privacy_policy_version = settings.LEGAL_PRIVACY_VERSION
            user.set_password(QA_PASSWORD)
            user.save()

            if definition.get("join_request") and organization is not None:
                OrganizationJoinRequest.objects.get_or_create(
                    organization=organization,
                    requester=user,
                    status=OrganizationJoinRequest.Status.PENDING,
                    defaults={"expires_at": timezone.now() + timedelta(days=14)},
                )

            rows.append(
                (
                    definition["username"],
                    organization.business_name if organization else "(plataforma)",
                    definition["purpose"],
                )
            )
        return rows

    def _print_summary(self, rows: list[tuple]) -> None:
        self.stdout.write(self.style.SUCCESS("QA test users seeded."))
        self.stdout.write(f"Password (todos): {QA_PASSWORD}")
        self.stdout.write("")
        for username, organization, purpose in rows:
            self.stdout.write(f"- {username} [{organization}]")
            self.stdout.write(f"    {purpose}")
