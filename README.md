# VIMER

Documento autoritativo del proyecto. Este `README.md` consolida la documentación funcional, técnica y operativa de VIMER.

## Resumen

VIMER es un MVP en Django para conectar organizaciones demandantes y oferentes alrededor de retos de I+D+i.

Estado actual:
- Base funcional de desarrollo operativa.
- Flujo principal implementado: registro, login, listado de desafíos, detalle, publicación de retos y postulación.
- No está listo para producción: faltan endurecimiento de seguridad, pruebas más amplias y cierre de brechas operativas.

## Dominio

VIMER modela tres conceptos centrales:
- `Organization`: entidad jurídica con rol de mercado único, `DEMANDANTE` u `OFERENTE`.
- `Challenge`: reto o necesidad de I+D+i publicada por una organización demandante.
- `Application`: propuesta técnica enviada por una organización oferente a un desafío.

Lenguaje ubicuo:
- Demandante: publica desafíos.
- Oferente: postula soluciones.
- Representante: usuario humano que opera en nombre de una organización.

## Arquitectura

El proyecto sigue una separación simple por apps:

```text
config/          Configuración Django
apps/identity/   Usuario personalizado, registro y autenticación
apps/corporate/  Organizaciones y rol de mercado
apps/marketplace/Desafíos y postulaciones
templates/       Plantillas HTML
```

Modelos principales:
- `identity.User`: extiende `AbstractUser` y se vincula a `corporate.Organization`.
- `corporate.Organization`: almacena NIT, razón social, rol y datos de contacto.
- `marketplace.Challenge`: reto publicado por un demandante.
- `marketplace.Application`: solución propuesta por un oferente.

## Funcionalidad implementada

- Registro unificado de usuario y organización.
- Login y logout.
- Protección de marketplace para usuarios autenticados.
- Navegación condicionada por rol.
- Publicación de retos por organizaciones demandantes.
- Postulación a retos por organizaciones oferentes.
- Administración básica en Django admin.
- Contenerización básica con `Dockerfile` y `docker-compose.yml`.

## Reglas de negocio vigentes

- El NIT de una organización es único.
- Solo organizaciones `DEMANDANTE` pueden publicar desafíos.
- Solo organizaciones `OFERENTE` pueden aplicar a desafíos.
- Una organización no puede aplicar dos veces al mismo desafío.

Las restricciones de rol están implementadas hoy sobre todo en lógica de aplicación y validaciones de modelo. No existe todavía una capa completa de constraints de base de datos para todas las invariantes del dominio.

## Estado real del proyecto

Fortalezas:
- El proyecto arranca y `python manage.py check` no reporta errores.
- El repositorio está estructurado y la rama actual es `foundation`.
- El dominio central ya está modelado y navegable.

Limitaciones actuales:
- El perfil por defecto sigue siendo de desarrollo.
- La seguridad de despliegue depende de variables de entorno correctas.
- No hay todavía una suite de pruebas amplia.
- Se usa SQLite como base por defecto.

## Correcciones aplicadas en esta consolidación

Se corrigieron fallos prioritarios detectados durante la auditoría:
- Se añadió la plantilla faltante para crear desafíos.
- Se corrigió el logout para usar `POST`, evitando el `405` del enlace por `GET`.
- Se pasó el desafío al contexto del formulario de postulación.
- El registro ahora solicita y guarda `contact_phone`, alineado con el modelo.
- Se definió `ASGI_APPLICATION`.
- `ALLOWED_HOSTS` tiene un default local seguro y compatible con pruebas (`localhost`, `127.0.0.1`, `[::1]`, `testserver`).
- Se agregaron pruebas mínimas para los flujos más críticos.

## Rutas principales

- `/signup/`: registro de usuario y organización
- `/login/`: inicio de sesión
- `/logout/`: cierre de sesión por `POST`
- `/marketplace/`: listado de desafíos
- `/marketplace/challenge/create/`: creación de desafío
- `/marketplace/challenge/<id>/`: detalle de desafío
- `/marketplace/challenge/<id>/apply/`: envío de propuesta
- `/admin/`: administración

## Requisitos

- Python 3.12+
- Django 6.0.x
- Pillow
- django-environ

Dependencias definidas en [requirements.txt](requirements.txt).

## Configuración local

1. Crear entorno virtual e instalar dependencias.
2. Definir `.env` si se necesitan valores explícitos.
3. Ejecutar migraciones.
4. Crear superusuario si hace falta.
5. Levantar el servidor.

Comandos:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Variables de entorno relevantes:
- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `DATABASE_URL`
- `CSRF_TRUSTED_ORIGINS`

Comportamiento por entorno:
- Desarrollo: `DEBUG=True`, SQLite por defecto, cookies seguras desactivadas y `ALLOWED_HOSTS` locales automáticos.
- Producción: requiere `SECRET_KEY`, permite `DATABASE_URL` externo y activa por defecto HSTS, cookies seguras y redirect a HTTPS salvo override explícito por entorno.

## Docker

El proyecto incluye:
- `Dockerfile`
- `docker-compose.yml`

Actualmente ambos usan `runserver`, por lo que sirven para desarrollo, no para producción.

## Verificación

Comandos útiles:

```bash
python manage.py check
python manage.py check --deploy
python manage.py test
```

## Pendientes prioritarios

- Endurecer configuración de producción (`DEBUG=False`, cookies seguras, HSTS, SSL redirect).
- Migrar a un servidor y stack de producción reales.
- Añadir más pruebas de permisos, validaciones y errores de negocio.
- Evaluar constraints de base de datos para reforzar invariantes.
- Mejorar UX de formularios y plantillas.
- Definir estrategia de despliegue y persistencia más allá de SQLite.

## Notas de documentación

Este archivo reemplaza como referencia del proyecto a la documentación de estado dispersa previa. Los archivos Markdown auxiliares sobre Django 6.0 son notas de referencia local y no forman parte de la documentación funcional de VIMER.
