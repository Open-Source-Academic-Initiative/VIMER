# Validación de VIMER v1

## 1. Decisión

`NO_APTO_PARA_PRODUCCION` — `NO_APTO_PARA_PRODUCCION_POR_VALIDACION_PENDIENTE`.

La candidata tiene las correcciones aplicadas y la matriz funcional validada.
La aceptación del entorno público sigue abierta: dominio y certificado reales,
entrega SMTP, Turnstile y datos definitivos del responsable. Las pruebas de
infraestructura usan un certificado confiado únicamente para la prueba y
configuración ficticia; no prueban esos servicios externos. Revisar esta
candidata y cerrar esa aceptación antes de promoverla. El piloto activo no fue
actualizado ni aprobado.

## 2. Cambios realizados

| Archivos | Problema demostrado | Solución y razón |
| --- | --- | --- |
| `apps/marketplace/application_views.py`, `apps/marketplace/tests.py` | La URL de postulación exponía desafíos privados; el convocante podía descargar adjuntos de propuestas en borrador al cerrar o adjudicar. | Reutilizar el queryset de visibilidad y exigir propuesta enviada para el acceso del convocante. Pruebas negativas GET/POST y de descarga tras ambos cambios de estado. |
| `apps/marketplace/models.py`, migración `0012_application_application_status_matches_submission_date.py` | La base aceptaba estados de propuesta incompatibles con la fecha de envío. | `CheckConstraint` nativa: borrador sin fecha o enviada con fecha. Se verifica también mediante escrituras que omiten la validación del modelo. |
| `config/settings.py`, `config/testing.py`, `apps/marketplace/test_postgresql_concurrency.py` | Producción rechazaba SQLite y dos escritores producían `database is locked`. | Motor independiente del perfil; SQLite usa `IMMEDIATE` nativo y la misma lógica transaccional. Las dos carreras se prueban en ambos motores con conexiones independientes y SQLite en archivo. |
| `apps/marketplace/models.py` | El mismo validador de adjuntos se ejecutaba en el campo y en `clean()`. | Conservar la validación nativa de `FileField` y `full_clean()`; retirar la llamada duplicada. |
| `config/settings.py`, `apps/identity/test_ui_accessibility.py` | CSP permitía estilos inline; el administrador de Django requiere estilos dinámicos. | Procesador de contexto y nonce nativos de Django 6.1; retirar `unsafe-inline` y probar el estilo del administrador contra el nonce de la cabecera. |
| `config/settings.py`, `config/tests.py`, `deploy/nginx/vimer.conf` | El acceso al administrador no tenía el límite de intentos del acceso público. | Reutilizar el límite existente en Django y la zona de Nginx para `/admin/login/`, con regresión de respuesta 429. |
| `requirements.txt`, `requirements.lock`, `requirements-dev.lock` | Django 6.0.7 estaba desactualizado; sqlparse 0.5.5 tenía cinco avisos únicos. | Django 6.1.2 y sqlparse 0.6.0, fijados con hashes. Se conservan las demás versiones del lock. |
| `Dockerfile`, `deploy/nginx/Dockerfile`, `deploy/postgresql/Dockerfile`, `docker-compose.production.yml` | Las imágenes fijadas contenían vulnerabilidades críticas y altas. | Parches puntuales de Alpine en VIMER; Nginx estable 1.30.5 con dos parches; PostgreSQL 16.15 como `postgres`, sin el programa auxiliar `gosu` vulnerable e innecesario. Imágenes oficiales base fijadas por digest y escaneos sin exclusiones. |
| `docker-compose.yml`, `docker-compose.pilot.yml`, `docker-compose.production.yml`, `.env.example` | Compose imponía el motor, no compartía SQLite en producción y el scheduler podía arrancar antes de las migraciones. | `DATABASE_URL` configurable, PostgreSQL opcional, directorio persistente compartido y dependencia nativa de la salud de la web. Se conservan los controles de producción. |
| `deploy/ops/backup.sh`, `deploy/ops/restore.sh`, `deploy/ops/sqlite_restore.py`, `config/tests.py` | Respaldo/restauración elegían el motor por perfil; restaurar SQLite sustituía los permisos del archivo operativo. | Elegir el respaldo por URL y restaurar por contenido del paquete. Preservar UID/GID y permisos antes del reemplazo atómico, sin modificar el destino si falla esa preservación. |
| `Makefile`, `config/tests.py` | El check de despliegue y sus regresiones no demostraban ambos motores. | Permitir `DATABASE_URL` en el comando existente y probar que ambos conservan los controles de seguridad. |
| `README.md`, `docs/operations.md`, `docs/release_plan_v1.md`, `docs/testing_strategy.md`, ADR `0004` y `0006`, este informe | Versiones, matriz y controles descritos ya no correspondían al comportamiento. | Actualizar únicamente esos contratos y enlazar una entrega estable. |

## 3. Django-first

Se reutilizan ORM, QuerySets existentes, `ModelForm`, autenticación, sesiones,
CSRF, recuperación de contraseña, validadores, `FileField`, `full_clean()`,
`UniqueConstraint`, `CheckConstraint`, `atomic()`, migraciones, comandos de
gestión, middleware de seguridad y CSP nativa. Se eliminó una validación de
archivo repetida; no se añadieron dependencias Python ni capas de negocio.

Permanecen la autorización por organización y estado, las transiciones del
dominio, la verificación de correo, Turnstile y el límite de intentos existente:
el core no resuelve esos requisitos completos. Los validadores de adjuntos
conservan la lista permitida y la comprobación de contenido requerida.

Django 6.1.2 amplía el soporte hasta diciembre de 2027 y pasó la matriz. La
siguiente migración prevista es 6.2 LTS, tras su publicación prevista para
abril de 2027. [Calendario oficial de Django](https://www.djangoproject.com/download/),
[notas de Django 6.1.2](https://docs.djangoproject.com/en/6.1/releases/6.1.2/).

## 4. Compatibilidad de bases de datos

| Verificación | SQLite | PostgreSQL |
| --- | --- | --- |
| Instalación limpia con hashes | Correcta | Correcta, incluido psycopg |
| Migraciones desde base vacía | 52 aplicadas, RC 0 | 52 aplicadas, RC 0 |
| `check` y `check --deploy` | Sin incidencias, RC 0 | Sin incidencias, RC 0 |
| `makemigrations --check --dry-run` | Sin cambios, RC 0 | Sin cambios, RC 0 |
| Suite completa local final | 205 pruebas, RC 0 | 205 pruebas, RC 0 |
| Invariantes y carreras | Se ejecutan | Se ejecutan |
| Producción en Docker | 205 pruebas, HTTPS, descarga privada y respaldo/restauración: RC 0 | 205 pruebas, HTTPS, descarga privada y respaldo/restauración: RC 0 |

Las dos omisiones de cada suite son controles Axe opcionales; no se omiten
pruebas por motor. Los servicios de negocio son comunes. `IMMEDIATE` serializa
los escritores de SQLite al entrar en `atomic()`; no certifica un SLA de carga.
Durante las dos suites simultáneas en ASUS, la comprobación de salud de la
candidata SQLite agotó el plazo de 6 segundos, con cero reinicios. La presión
de recursos es una hipótesis; no se aumentó el plazo ni se certificó capacidad.
Tras la restauración, web y scheduler volvieron a estar saludables y la
descarga completa del adjunto pasó otra vez.
[Contrato oficial de SQLite en Django](https://docs.djangoproject.com/en/6.1/ref/databases/#sqlite-notes).

La migración también pasó sobre una copia de la base SQLite operativa, con
conteos preservados. Los 435 archivos originales inventariados conservaron
sus hashes. Los datos operativos no se migraron durante esta revisión.

## 5. Seguridad

- **Críticos y altos:** corregidos los hallazgos de autorización y las
  dependencias vulnerables. `pip-audit` final y Trivy sobre las tres imágenes
  corregidas no reportan vulnerabilidades conocidas en sus ámbitos auditados;
  Trivy se ejecuta para críticos/altos, sin exclusiones ni `ignore-unfixed`.
- **Medios bloqueantes:** no se identificaron en el delta revisado. La
  aceptación externa indicada en la decisión sigue pendiente.
- **Endurecimiento:** se mantienen CSRF, cookies seguras, HSTS, CSP, archivos
  privados, validación de configuración, contenedores de aplicación de solo
  lectura, `tmpfs`, `no-new-privileges`, salud y rotación de logs.

El certificado de la prueba se valida como CA explícita; no se desactiva la
verificación TLS. La descarga privada se prueba mediante Nginx y
`X-Accel-Redirect`. Se generan SBOM de Python y de cada imagen. PostgreSQL usa
su usuario nativo conforme al [contrato oficial de la imagen](https://hub.docker.com/_/postgres#arbitrary---user-notes).

## 6. Evidencia de validación

El registro [comandos.jsonl](../artifacts/audit/validacion_v1_2026-10-06/comandos.jsonl)
contiene argumentos, entorno seleccionado, RC, duración y hash del log de
cada validación registrada, incluidos los fallos reproducidos y los errores corregidos
del montaje de pruebas. Las credenciales de los montajes son ficticias. En
las órdenes SSH, el entorno registrado es el del orquestador; los entornos de
los contenedores se conservan en `compose-{motor}.env` y en el script.

| Comando realmente ejecutado | RC | Registro |
| --- | --- | --- |
| `python -m pip --python /tmp/vimer-v1-release/bin/python install --require-hashes --only-binary=:all: -r requirements-dev.lock` | 0 | `instalacion_final_hashes.log` |
| `.venv/bin/python -m pip --python /tmp/vimer-v1-release/bin/python check` | 0 | `pip_integridad_corregida.log` |
| `/tmp/vimer-v1-release/bin/python manage.py test --parallel 4 --noinput`, con cada URL | 0 / 0 | `sqlite_suite_definitiva.log`, `postgresql_suite_definitiva.log` |
| `manage.py migrate --noinput`, con cada URL y bases vacías | 0 / 0 | `sqlite_migracion_vacia.log`, `postgresql_migracion_vacia_autorizada.log` |
| `manage.py check`, `check --deploy`, `makemigrations --check --dry-run`, con cada URL | 0 | Registros `sqlite_*check*`, `postgresql_*check*` |
| `python -m ruff check .` | 0 | `lint_delta_final.log` |
| `make verify-fast` con el entorno local actualizado | 0 | `workspace_verificacion_final.log`: 205 pruebas, checks, migraciones, compilación y Ruff |
| `make compose-config` y `docker build ...` en ASUS | 0 | `asus_build_final.log`, `asus_preparar_certificacion.log`, construcciones de Nginx/PostgreSQL |
| `python -m pip_audit --strict --no-deps --disable-pip --requirement requirements.lock --format json --output artifacts/audit/validacion_v1_2026-10-06/python-audit-final.json` | 0 | `auditoria_final.log`, `python-audit-final.json` |
| `python -m cyclonedx_py requirements requirements.lock --output-reproducible --output-format JSON --output-file artifacts/audit/validacion_v1_2026-10-06/python-sbom.cdx.json` | 0 | `sbom_final.log`, `python-sbom.cdx.json` |
| `trivy image --scanners vuln --severity HIGH,CRITICAL --exit-code 1 ...`, tres imágenes | 0 | `asus_trivy_tres_corregidas.log`; imagen final en su registro definitivo |
| `sh /home/andres/Desarrollo/vimer/artifacts/audit/validacion_v1_2026-10-06/validar_stack.sh sqlite` y el mismo script con `postgresql`, en ASUS | 0 / 0 | `asus_stack_sqlite_certificacion.log`, `asus_stack_postgresql_certificacion.log` |

Los comandos completos, los SBOM y los informes JSON están en
[la carpeta de evidencia](../artifacts/audit/validacion_v1_2026-10-06/).
El manifiesto SHA-256 identifica la entrega. No se sustituyen los resultados
de pruebas por una afirmación de estabilidad operativa.

## 7. Deuda técnica no bloqueante

1. Medir capacidad y contención antes de escalar escritores de SQLite.
2. Evaluar los nuevos mailers nativos al planear Django 6.2 LTS; el backend
   SMTP vigente sigue funcionando en 6.1.
3. Completar revisión manual y Axe si se quiere declarar conformidad WCAG;
   esta entrega no hace esa declaración.

## 8. Identificación de versión

- Commit inicial: `b4fdf85b27a01b36fe68e91265a9b7f7a9488610`.
- Commit final: el mismo HEAD; el delta está aplicado sin commit ni promoción.
  Sus fuentes y hashes se registran en la evidencia.
- Django: **6.1.2**; sqlparse: **0.6.0**, también instalados en `.venv`.
- Python: **3.12.3** en la validación local; **3.12.13** en Docker.
- SQLite: **3.45.1** local; **3.53.4** en Docker.
- PostgreSQL: **16.15**, instancia temporal local e imagen candidata.
- Nginx: **1.30.5**; Trivy: **0.72.0** con base actualizada el 6 de octubre.
- Imagen de aplicación candidata: `vimer:revision-v1-20261006-segura`, ID
  `4131a24380f9`. Los IDs completos de las tres imágenes están en la evidencia.

Fecha de validación: 6 de octubre de 2026. Los proyectos temporales de Docker
se eliminan al terminar sus pruebas; se conservan las imágenes candidatas y
la evidencia. Los dos contenedores `vimer-review-*` conservan su identidad y
su arranque originales.
