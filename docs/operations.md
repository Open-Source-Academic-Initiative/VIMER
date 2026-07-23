# Operación segura de VIMER

Esta guía cubre los perfiles `pilot` (SQLite) y `production` (PostgreSQL +
Nginx/TLS) con Docker Compose v1. Los comandos deben ejecutarse desde la raíz
del repositorio.

## Preparación

1. Copiar `.env.example` a `.env` y reemplazar todos los marcadores
   `CHANGE_ME`. `.env` nunca se versiona.
2. Para el piloto, crear `data/` y `media/`. SQLite vive únicamente en
   `data/db.sqlite3`; se monta el directorio completo y no un archivo
   preexistente, lo que evita que Docker convierta accidentalmente una ruta de
   archivo inexistente en un directorio.
3. Para producción, aprovisionar los archivos TLS fuera del repositorio y
   definir `TLS_CERTIFICATE_PATH` y `TLS_PRIVATE_KEY_PATH`. El proceso de
   Nginx debe poder leerlos.
4. Validar la configuración sin imprimir el entorno:

   ```sh
   make compose-config
   make check-deploy
   ```

`config/settings.py` aborta el arranque de producción ante `DEBUG=True`, una
clave secreta débil o de ejemplo, SQLite, hosts no explícitos, orígenes CSRF o
URL pública sin HTTPS, Turnstile incompleto, correo por consola, credenciales
SMTP de ejemplo, controles HTTPS desactivados o datos legales ausentes.
También exige Turnstile y entrega de correo en cualquier piloto con
`DEBUG=False`. El opt-out explícito (`TURNSTILE_REQUIRED=False` y
`EMAIL_DELIVERY_REQUIRED=False` con backend de consola) se reserva para un
entorno cerrado de mantenimiento que no admite participantes; producción lo
rechaza siempre.

Los datos del responsable legal son configuración operacional y no deben
inventarse en código:

- `LEGAL_CONTROLLER_NAME`
- `LEGAL_CONTROLLER_ID`
- `LEGAL_CONTROLLER_ADDRESS`
- `LEGAL_CONTROLLER_CONTACT_CHANNEL`
- `PRIVACY_EMAIL`

## Arranque y actualización

El `entrypoint` valida el despliegue, espera la base de datos, ejecuta
`migrate --noinput`, ejecuta `collectstatic --noinput` y finalmente inicia
Gunicorn. Sus logs de acceso y error salen por stdout/stderr.

Un servicio `scheduler` separado ejecuta periódicamente los comandos atómicos e
idempotentes `expire_join_requests` y `close_expired_challenges`. No comparte
un loop con Gunicorn y no ejecuta migraciones ni `collectstatic`; primero exige
que no haya migraciones pendientes. Cada job conserva su propio intervalo,
reintento y marca de último éxito. El fallo de uno se registra y reintenta sin
impedir la ejecución del otro, y el healthcheck falla si cualquiera queda
obsoleto. Debe existir exactamente una réplica del scheduler:

```sh
docker-compose -f docker-compose.production.yml ps scheduler
docker-compose -f docker-compose.production.yml logs --tail=100 scheduler
```

Los intervalos se configuran con `JOIN_REQUEST_EXPIRY_INTERVAL_SECONDS` y
`CHALLENGE_CLOSURE_INTERVAL_SECONDS`; ninguno puede ser menor a 60 segundos.
`SCHEDULER_RETRY_DELAY_SECONDS` controla el reintento tras error y
`SCHEDULER_HEALTH_GRACE_SECONDS` la tolerancia del healthcheck.

Las ramas concurrentes
`notifications.0003_alter_notification_kind` y
`notifications.0003_lifecycle_notification_kinds` se conservan intactas.
`notifications.0004_merge_notification_kind_choices` depende de ambas y fija
explícitamente la unión de tipos de identidad y ciclo de vida; no se debe
renumerar ni reescribir una rama `0003` que pueda haberse aplicado.

Antes de una actualización:

```sh
docker-compose -f docker-compose.production.yml stop web scheduler
VIMER_BACKUP_WRITES_QUIESCED=True \
  sh deploy/ops/backup.sh production /ruta/segura/fuera-del-repositorio
docker-compose -f docker-compose.production.yml build --pull
docker-compose -f docker-compose.production.yml up -d
docker-compose -f docker-compose.production.yml ps
```

Revisar siempre las migraciones y el plan de reversión antes de `up`. El
arranque automático está pensado para una sola réplica web; si se escala a
varias réplicas, las migraciones deben convertirse en un único trabajo de
release coordinado.

En piloto:

```sh
docker-compose -f docker-compose.pilot.yml stop web scheduler
VIMER_BACKUP_WRITES_QUIESCED=True \
  sh deploy/ops/backup.sh pilot /ruta/segura/fuera-del-repositorio
docker-compose -f docker-compose.pilot.yml up -d --build
```

No ejecutar el `entrypoint` como mecanismo de prueba sobre una base operativa.
Las validaciones de código usan la base temporal creada por el test runner.

## TLS y proxy

Nginx atiende ACME y `/nginx-health` por HTTP; el resto recibe una redirección
308 a HTTPS. En HTTPS envía siempre `X-Forwarded-Proto: https`, y Django solo
confía esa cabecera en el perfil de producción mediante
`SECURE_PROXY_SSL_HEADER`. Esta pareja evita el bucle de redirección TLS.

Tras renovar un certificado montado como archivo, recrear Nginx para garantizar
que Docker vea el archivo nuevo:

```sh
docker-compose -f docker-compose.production.yml up -d --force-recreate nginx
```

Comprobar desde otra máquina:

```sh
curl -I http://vimer.example.org/
curl -I https://vimer.example.org/
curl -fsS https://vimer.example.org/health/live/
curl -fsS https://vimer.example.org/health/ready/
```

`/health/live/` comprueba que Django responde. `/health/ready/` devuelve 200
solo si la base responde y no hay migraciones pendientes; en otro caso devuelve
503 sin exponer detalles internos. El healthcheck de Nginx es local y el de
`web` usa readiness.

## Datos de SQLite existentes

Una instalación antigua puede tener `./db.sqlite3`. No se mueve ni elimina
automáticamente. Con el servicio detenido y después de un respaldo verificado:

```sh
VIMER_SQLITE_PATH=./db.sqlite3 \
  VIMER_BACKUP_WRITES_QUIESCED=True \
  sh deploy/ops/backup.sh pilot /ruta/segura/fuera-del-repositorio
test ! -e data/db.sqlite3
mkdir -p data
cp --preserve=mode,timestamps db.sqlite3 data/db.sqlite3
python3 -c 'import sqlite3; db=sqlite3.connect("data/db.sqlite3"); print(db.execute("PRAGMA integrity_check").fetchone()[0])'
```

El resultado debe ser `ok`. Conservar el archivo original hasta completar las
pruebas funcionales y un segundo respaldo.

## Respaldo y restauración

Los respaldos crean una carpeta fechada nueva con base de datos, medios (si
existen) y `MANIFEST.sha256`; una colisión de nombre falla en vez de mezclar
artefactos. SQLite usa su API de backup y valida integridad; PostgreSQL usa
`pg_dump` en formato custom. En producción, un contenedor efímero de la imagen
web lee el volumen de medios sin iniciar Django.

La base y los medios solo forman un punto consistente si no hay escrituras
durante ambas capturas. Detener `web` y `scheduler`; el script exige la
confirmación explícita `VIMER_BACKUP_WRITES_QUIESCED=True`:

```sh
docker-compose -f docker-compose.pilot.yml stop web scheduler
VIMER_BACKUP_WRITES_QUIESCED=True \
  sh deploy/ops/backup.sh pilot /mnt/backups/vimer
docker-compose -f docker-compose.pilot.yml start web scheduler

docker-compose -f docker-compose.production.yml stop web scheduler
VIMER_BACKUP_WRITES_QUIESCED=True \
  sh deploy/ops/backup.sh production /mnt/backups/vimer
docker-compose -f docker-compose.production.yml start web scheduler
```

Copiar el respaldo a almacenamiento separado y ensayar la restauración
periódicamente en un entorno aislado. Para restaurar, detener `web`, elegir
exactamente la carpeta de respaldo y usar la confirmación explícita:

```sh
docker-compose -f docker-compose.pilot.yml stop web scheduler
sh deploy/ops/restore.sh pilot /mnt/backups/vimer/vimer-pilot-FECHA --confirm

docker-compose -f docker-compose.production.yml stop web scheduler
RESTORE_MEDIA=True \
  sh deploy/ops/restore.sh production \
  /mnt/backups/vimer/vimer-production-FECHA --confirm
```

La restauración verifica hashes y rechaza rutas, enlaces y tipos especiales
peligrosos dentro del tar. `RESTORE_MEDIA=True` es deliberadamente opt-in. Los
medios previos del piloto se renombran; en producción se guardan como un tar
`media.pre-restore-*` dentro de la carpeta del respaldo antes de reemplazarlos.
Después se deben ejecutar checks y pruebas de humo antes de iniciar `web`.

## Límites, abuso y observabilidad

Nginx limita el cuerpo a 55 MiB. Django aplica el mismo límite total, conserva
solo 2 MiB por archivo en memoria y limita campos/archivos; el dominio mantiene
el máximo de cinco adjuntos de 10 MiB. Los límites de login, registro,
restablecimiento de contraseña y verificación de correo se aplican en Nginx y
como red de seguridad cacheada en Django. Turnstile es obligatorio y
fail-closed en producción.

Los servicios usan `restart: unless-stopped`, healthchecks y rotación del
driver `json-file` (cinco archivos de 10 MiB). Revisar:

```sh
docker-compose -f docker-compose.production.yml ps
docker-compose -f docker-compose.production.yml logs --tail=200 web nginx db
```

Para múltiples contenedores web, reemplazar el cache local del rate limit por
un backend compartido antes de escalar.

## Dependencias, SCA y SBOM

La aplicación exige Django `6.0.7` y mantiene un `requirements.lock` exacto
con hashes. La imagen exige esos hashes al instalar; una dependencia o
artefacto no declarado hace fallar el build.

Los locks se generan con Python 3.12 y `pip-tools==7.6.0`, preservando las
versiones revisadas mediante el lock anterior como constraint:

```sh
python3 -m venv .venv-lock
.venv-lock/bin/python -m pip install pip-tools==7.6.0
.venv-lock/bin/pip-compile --generate-hashes \
  --strip-extras \
  --no-annotate \
  --no-emit-index-url \
  --no-emit-trusted-host \
  --resolver=backtracking \
  --constraint requirements.lock \
  --output-file=requirements.lock requirements.txt
.venv-lock/bin/pip-compile --generate-hashes \
  --strip-extras \
  --no-annotate \
  --no-emit-index-url \
  --no-emit-trusted-host \
  --resolver=backtracking \
  --constraint requirements.lock \
  --output-file=requirements-dev.lock requirements-dev.txt
```

Para una actualización intencional de versiones, generar el lock sin
`--constraint requirements.lock`, revisar el diff y validar la instalación
con `pip install --require-hashes -r requirements.lock`. Las imágenes base
están fijadas por versión y digest; para actualizarlas, resolver el nuevo digest con
`docker buildx imagetools inspect`, revisar el cambio y volver a escanear.

Las herramientas de seguridad están separadas en
`requirements-security.txt`, para no contaminar el runtime:

```sh
python3 -m venv .venv-security
.venv-security/bin/python -m pip install -r requirements-security.txt
PATH="$PWD/.venv-security/bin:$PATH" \
  VIMER_IMAGE=vimer:production \
  sh deploy/ops/security_scan.sh
```

El script ejecuta `pip-audit` y genera SBOM CycloneDX de Python y de la imagen.
Trivy conserva todos los hallazgos `HIGH`/`CRITICAL` en
`container-audit.json`; el gate accionable queda en
`container-actionable-audit.json` y falla cuando existe una versión corregida
disponible que la imagen todavía no incorpora. Los hallazgos sin
`FixedVersion` tampoco se ocultan: permanecerían en el reporte completo y
exigirían la aceptación temporal descrita en
`docs/operations/container_vulnerability_risk.md`. Trivy debe instalarse desde
su distribución oficial y fijarse por versión/digest en CI. Para generar solo
los artefactos Python cuando la imagen aún no existe, usar
`SCAN_CONTAINER_IMAGE=False`. Los resultados quedan bajo
`artifacts/security/` y se acompañan de hashes.

Bleach `6.4.0` corrige los advisories aplicables al uso de `bleach.clean`.
`GHSA-g75f-g53v-794x` afecta exclusivamente
`bleach.linkify(parse_email=True)`, API que VIMER no invoca, y queda como
excepción explícita y revisable del escáner. Bleach ya no recibe mantenimiento;
migrar el sanitizador a una alternativa mantenida sigue siendo deuda de
seguridad. Para volver a evaluar sin la excepción:

```sh
PIP_AUDIT_IGNORED_VULNERABILITIES='' \
  SCAN_CONTAINER_IMAGE=False sh deploy/ops/security_scan.sh
```

## Validación y accesibilidad

```sh
make verify-fast
make compose-config
```

El `TEST_RUNNER` global sustituye `MEDIA_ROOT` por un directorio temporal y lo
elimina incluso si la suite falla. No borrar ni reutilizar `media/` para tests.
Para una verificación adicional, comparar un inventario o hash de `media/`
antes y después de la suite.

Antes del release:

```sh
.venv/bin/python -m pip install --require-hashes -r requirements.lock
.venv/bin/python -m pip install --require-hashes -r requirements-dev.lock
.venv/bin/python -m pip check
.venv/bin/python -c 'import django; print(django.get_version())'
PATH="$PWD/.venv-security/bin:$PATH" sh deploy/ops/security_scan.sh
```

La versión impresa de Django debe ser `6.0.7`; validar el lock con hashes en
un venv limpio antes de construir la imagen.

Axe se ejecuta de forma opt-in con versiones fijadas de Firefox, Selenium y
`axe-core`, sin mezclarlas con el lock Python de runtime. La validación
automatizada complementa, pero no reemplaza, las pruebas de teclado, foco,
zoom, contraste y lector de pantalla.
