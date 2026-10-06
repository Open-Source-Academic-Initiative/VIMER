# VIMER: candidata publicada para pruebas locales

**Abra [VIMER en la red local](http://192.168.0.10:8088)** y revise el ingreso,
el borrador, el envío de propuestas y la descarga de archivos. Sus cuentas
anteriores se conservaron. Los registros añadidos por la comprobación llevan
el nombre «Prueba local beta»; las cuentas de prueba están protegidas en ASUS.

## 1. Dictamen

**`NO_APTO_PARA_BETA_ESTABLE`**. Estado del alcance solicitado:
**`PUBLICADO_PARA_PRUEBAS_MANUALES_LOCALES`**.

El usuario acotó la publicación: «Por ahora se publica en local para pruebas
manuales». La candidata pasó la aceptación técnica local. La revisión manual
y la aceptación pública siguen pendientes; la etiqueta local identifica una
candidata y no declara estabilidad general. Fecha: 6 de octubre de 2026.

## 2. Entorno y alcance comprobado

ASUS `192.168.0.10`, contexto Docker `default`, Docker 29.1.3 y Compose 5.5.1.
URL única: `http://192.168.0.10:8088`. Proyecto: `vimer-review`, con un servicio
web y un `scheduler`. Motor vigente: SQLite 3.53.4; Django 6.1.2 y Python
3.12.13. Se conserva `DEBUG=False`; el perfil local usa correo de consola y
Turnstile desactivado, como en el entorno de revisión anterior. Se mantienen
CSRF, CSP, autorización de archivos y controles de cuentas. Se activó
`SECURE_CONTENT_TYPE_NOSNIFF=True`.

Carga exploratoria: 4 lectores y 2 escritores HTTP durante 30,41 segundos;
571 lecturas y 284 escrituras, sin errores inesperados ni `database is locked`.
Latencia p95: 118,18 ms en lectura y 70,18 ms en escritura. Los dos servicios
estuvieron sanos en las muestras, con cero reinicios automáticos. Se conservaron
un trabajador Gunicorn y el timeout de salud de 6 segundos. Esta observación
no acredita un SLA ni la causa del timeout histórico durante suites simultáneas.

## 3. Identificación de la versión

Commit de las fuentes verificadas:
`ae9483d45f33e5d87847351a2632b20d5d2602e9`.
Etiqueta anotada local: `v0.0.2b1-local`, ligada a ese commit; sin push.

Imagen efectiva de ambos servicios, fijada por ID completo en Compose:
`sha256:4131a24380f9987a8b62e4af94cbba1401d42c5067f3504aa32d41cadf2360e4`.
Etiqueta de construcción: `vimer:revision-v1-20261006-segura`.
Los hashes de 205 fuentes de ejecución, plantillas, scripts y locks coinciden
entre imagen y commit; la documentación de cierre es posterior al build.
La imagen validada se reutilizó sin reconstrucción.

Archivos canónicos: `docker-compose.pilot.yml` y
`artifacts/runtime/vimer-review.override.yml`; interpolación protegida en
`artifacts/runtime/vimer-review.env`. [Operación del despliegue](operations.md#despliegue-local-vigente).

## 4. Inventario y retirada selectiva

| Recurso | Antes | Después |
| --- | --- | --- |
| Web VIMER | Piloto `61fec88df970…` | Candidata `42cb8f90c14f…`, sana |
| Scheduler VIMER | Piloto `d09bed0d08a8…` | Candidata `aebd0d23a709…`, sana; una réplica |
| Contenedor antiguo `vimer` | Detenido `eac89d92264e…` | Retirado tras archivar su sistema de archivos y base |
| Contenedores del host | 9 | 8; los 6 ajenos conservan IDs, imágenes, inicio, montajes y puertos |
| Imágenes del host | 340 | 335; retiradas 5 imágenes VIMER verificadas y sin consumidores |
| Volúmenes / redes originales | 9 / 6 | Todos preservados; red operativa reutilizada |

Se retiraron `vimer:test`, `vimer:pilot`, `vimer:infra-validation`,
`vimer:alpine-evaluation` y `vimer:revision-v1-20261006`; sus IDs completos y
resultados están en `recursos_retirados.json`. Nginx y PostgreSQL candidatos se
conservan para desarrollo; no están ejecutándose. No se borraron capas sin
atribución segura, datos ni recursos compartidos; no se ejecutó `prune`.
El ensayo de recuperación también quedó detenido y retirado, conservando sus
copias. No se encontraron automatismos VIMER adicionales en las unidades,
timers, cron del usuario y archivos de arranque accesibles. Docker conserva
`restart: unless-stopped` para los dos servicios actuales.

Se conservan `vimer-review_review_data`, `vimer-review_review_media` y
`vimer-review_pilot_static_data`, además de los tres volúmenes históricos
`vimer_*`. La base del repositorio, con datos distintos, permanece intacta;
no se fusionó ni se usó para reemplazar la base operativa.

## 5. Respaldo y recuperación

Recuperación protegida, fuera del despliegue activo:
`/home/andres/Backups/VIMER/cierre-beta-20261006T171610Z`.
Carpeta `0700`, configuración `0600`; 31 archivos verificados por SHA-256,
incluidas imágenes restauradas con `docker image load` y la capa completa del
contenedor antiguo. Manifiesto protegido: `MANIFEST_RECUPERACION.sha256`.

Respaldo final previo al corte: `copias/vimer-pilot-20261006T173546Z`.
Base y archivo de medios coinciden byte por byte con el respaldo ya restaurado
en un destino aislado. Se comprobaron integridad SQLite, claves foráneas,
hashes de todas las filas, cuatro referencias a archivos, contenido y permisos
`100:101`, modo `0644`. La copia restaurada arrancó con la candidata.

El corte detuvo primero el scheduler y luego web, respaldó los datos y aplicó
`marketplace.0012` una sola vez: 51 → 52 migraciones. Todas las filas de negocio
y los archivos previos se conservaron antes de abrir el puerto. El reinicio
controlado posterior conservó los datos y el adjunto de prueba descargable.

Para recuperar: cerrar escrituras; tomar un respaldo actualizado; verificar y
restaurar primero una copia aislada con los scripts nativos; validar permisos,
migraciones y referencias antes de reabrir la candidata. El respaldo previo al
corte no incluye las escrituras posteriores. No debe restaurarse sobre ellas
sin conciliación. Las imágenes antiguas archivadas no tienen aceptación para
exposición pública. [Procedimiento operativo](operations.md#respaldo-y-recuperación-del-despliegue-local).

## 6. Evidencia reutilizada y comprobaciones nuevas

Se verificaron los 156 archivos del manifiesto histórico, sin modificarlo:
`e472c2a8274b12c7ba80da1f82c943357b1d18c45c0263ab723813f7243da8a7`.
Las 242 fuentes históricas permanecían idénticas antes del commit. Se reutilizó
la matriz SQLite/PostgreSQL de 205 casos por motor, con dos omisiones opcionales
de Axe, y los análisis de dependencias e imágenes para esos mismos bytes.

Nuevas comprobaciones: inventarios, recuperación real, migración operativa,
HTTP/CSRF, ingreso y cierre por formularios, cuentas inactivas, aislamiento por
organización y estado, borrador, envío, descarga privada exacta, rechazo de
acceso directo, enlaces de correo locales, carga y persistencia tras reinicio.
La entrada LAN también respondió desde el cliente. No se repitieron suites
pesadas. Los intentos fallidos del guion de ensayo y la corrección de `nosniff`
se conservan; la comprobación de retirada inicialmente rechazó metadatos del
scheduler y pasó después de alinearlos con Compose.

Evidencia nueva: `artifacts/audit/cierre_beta_2026-10-06/`, con comandos, códigos
de retorno, resultados, identificación de imagen/commit y manifiesto propio.
La [validación anterior](validacion_v1.md) conserva su alcance histórico.

## 7. Pendientes y límites

Queda la revisión manual del usuario. Para publicación pública faltan dominio,
TLS y renovación, entrega SMTP a un destinatario autorizado, Turnstile real
con validación de tokens en servidor y datos definitivos del responsable,
incluido `PRIVACY_EMAIL`. La mera presencia de esos datos no certificará su
validez jurídica. El intento cerrado con la configuración existente y perfil
de producción fue rechazado por datos legales ausentes; no se relajaron sus
controles. No se verificaron entrega de correo, Turnstile ni TLS públicos.

La carga mide exclusivamente el escenario local indicado. La inspección de
automatismos abarca los archivos y contextos accesibles; no certifica otros
hosts ni cron de terceros. La aceptación visual en el navegador del usuario
y la aprobación de una beta estable siguen abiertas.
