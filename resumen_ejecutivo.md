# Resumen Ejecutivo - VIMER

Fecha: 2026-05-05
Rama de trabajo: `main`

## Estado general

VIMER ya no esta solo en una baseline funcional de Django. En la iteracion actual se consolido una base de dominio mucho mas explicita, se reforzo el flujo principal del marketplace y se abrio un cierre minimo pero real del ciclo `Desafio -> Propuesta -> Evaluacion -> Adjudicacion`.

Actualizacion 2026-05-05: el proyecto dio un segundo salto relevante. Ademas de la base DDD y del ciclo central ya consolidado, ahora existe una hoja de ruta de release v1 para piloto cerrado y una primera implementacion de capacidades operativas necesarias para ese piloto: onboarding multi-representante, aceptacion legal versionada, verificacion de email, Turnstile configurable, categorias, busqueda/filtros, adjuntos, markdown sanitizado, dashboard administrativo minimo y perfiles de despliegue `pilot`/`production`.

La fotografia correcta hoy es esta:

- El MVP sigue siendo navegable, estable y verificable.
- El proyecto ya cuenta con documentacion versionada de dominio en `docs/`.
- La ontologia canonica versionada del proyecto ahora vive en `docs/domain/ontology_v4.md`.
- El write-side principal ya no depende solo de vistas y forms; ahora se apoya en servicios de aplicacion explicitos.
- `Challenge` ya expresa estado, fecha limite y criterios de evaluacion.
- Los criterios de evaluacion ya no viven solo como texto libre; tambien existen como entradas estructuradas persistidas por desafio.
- `Application` ya funciona como una propuesta estructurada con lifecycle persistido `DRAFT -> SUBMITTED`, componentes obligatorios al enviar e inmutabilidad post-envio.
- El copy visible de marketplace y evaluation, junto con las pruebas de negocio de ambos subdominios, ya reflejan el lenguaje ubicuo de `Desafío` y `Propuesta`, sin renombrar aun artefactos tecnicos de persistencia.
- El cierre previsto de Fase 6 ya quedo materializado en el alcance actual: UI visible, pruebas de negocio y documentacion principal ya convergieron al lenguaje ubicuo aprobado.
- `Evaluation` ya existe como contexto explicito con:
  - inicio formal de evaluacion;
  - evaluacion por criterio;
  - evaluacion ciega antes de adjudicar;
  - multiples evaluadores por criterio;
  - adjudicacion con comentario obligatorio;
  - una sola propuesta ganadora por desafio.
- La evaluacion ya emite eventos de dominio despues del commit.
- Esos eventos ya alimentan historial del desafio y notificaciones internas.
- La revision de propuestas ya no depende solo de lectura manual: ahora existen resumenes agregados por propuesta con avance, puntaje acumulado, promedio, detalle por criterio y ranking comparativo explicito.
- El ranking de evaluacion ya no depende del volumen bruto de evaluaciones: ahora usa promedio entre criterios con el mismo valor para todos.
- La adjudicacion ya no solo registra comentario y propuesta ganadora: ahora conserva un snapshot del estado de evaluacion de la propuesta ganadora al momento de decidir, incluyendo contexto de mejor posicion, empates y decisiones excepcionales.
- La evaluacion por criterios ya emite un evento propio, con efecto visible en timeline y notificaciones al postulante evaluado.
- La actividad de evaluacion tambien ya produce notificaciones internas para el equipo de evaluacion y una auditoria publisher-facing mas rica.
- La adjudicacion ahora se bloquea si existe al menos una propuesta activa con criterios pendientes de evaluacion.
- Los empates tecnicos ya quedan visibles, comparten posicion compacta y pueden resolverse por criterio humano del adjudicador.
- La adjudicacion excepcional fuera del mejor lugar disponible ya existe, pero exige motivo estructurado, confirmacion explicita y justificacion libre obligatoria.
- La suite ya no depende por defecto del `.env` local para correr pruebas.
- La suite de pruebas mas pesada ya fue optimizada para reutilizar fixtures inmutables con `setUpTestData()`.
- El repositorio ahora expone una via estandar de validacion rapida con `make test-fast` y `make verify-fast`.
- El proyecto ya adopta capacidades concretas de Django 6.0 en el runtime real: `STORAGES`, `ContentSecurityPolicyMiddleware`, `SECURE_CSP`, `ASGI_APPLICATION`, `check --deploy` y serving con `gunicorn`.
- La alineacion con Django 6.0 no es total todavia: la CSP sigue permitiendo inline script/style por compatibilidad con templates actuales, y ni template partials ni el Tasks framework se usan aun en VIMER.
- El proceso de evaluacion ya no depende de permisos implicitos por pertenecer a la organizacion publicadora: ahora existe un equipo formal con evaluadores designados, un adjudicador designado y observadores.
- `Identity` ya soporta multiples representantes por organizacion, representante titular, solicitudes de union, aprobacion/rechazo por titular, expiracion de solicitudes, transferencia de titularidad, verificacion de correo y aceptacion versionada de terminos/politica.
- `Marketplace` ya soporta taxonomia cerrada de categorias, busqueda y filtros, adjuntos PDF/JPG/PNG en desafios y propuestas, y markdown sanitizado en contenido largo.
- La operacion ya distingue perfiles `pilot` y `production` mediante `DEPLOYMENT_PROFILE`; el perfil production pasa `manage.py check --deploy` cuando se proveen variables requeridas.
- Ya existe un dashboard minimo de administracion de plataforma en `/admin/dashboard/`.
- El proyecto sigue sin estar listo para produccion general, pero ya tiene una postura concreta para piloto cerrado.

## Cambios y acciones de esta sesion

En la sesion 2026-05-05 se ejecuto la consolidacion del release v1:

- Se creo `docs/release_plan_v1.md` como plan rector del piloto cerrado.
- Se agregaron ADRs 0004-0009: despliegue dual, onboarding multi-representante, adjuntos/markdown, taxonomia cerrada, postura de piloto y riesgos aceptados.
- Se implemento onboarding multi-representante con `OrganizationJoinRequest`, representante titular, aprobacion/rechazo, expiracion por comando y transferencia de titularidad.
- Se incorporaron verificacion de email, recuperacion de contrasena, aceptacion legal versionada y Turnstile configurable en signup.
- Se incorporaron categorias de desafio, busqueda y filtros en marketplace.
- Se implementaron adjuntos y markdown sanitizado para `Desafio` y `Propuesta`.
- Se agrego dashboard administrativo minimo y paginas publicas legales/FAQ.
- Se agregaron perfiles de despliegue y compose files separados para piloto y produccion.
- Se sincronizaron `README.md`, `docs/ddd_work_plan.md`, `docs/domain/*` y los documentos de seguimiento.
- Se valido el slice focal `apps.identity.tests apps.marketplace.tests apps.notifications.tests`: 62 tests OK.
- Se valido `DEPLOYMENT_PROFILE=production ... manage.py check --deploy`: sin issues.

## Cambios principales implementados

Durante esta iteracion local se implemento o consolido lo siguiente:

- Base documental DDD/ontologica versionada:
  - `docs/domain/ontology_v4.md`
  - `docs/ddd_work_plan.md`
  - `docs/domain/glossary.md`
  - `docs/domain/context_map.md`
  - `docs/domain/invariants.md`
  - `docs/templates/domain_feature_spec.md`
  - ADRs base en `docs/adr/`
- Reglas de dominio explicitas en `apps/marketplace/domain/` para publication y application invariants.
- Servicios de aplicacion explicitos en `identity`, `marketplace`, `evaluation` y `notifications`.
- Separacion tactica interna de `marketplace` entre challenge y application tambien en:
  - formularios
  - vistas
  - consumo de urls desde entrypoints separados
  - cobertura automatizada por subdominio
- Evolucion de `Challenge` con:
  - `status`
  - `application_deadline`
  - `evaluation_criteria`
  - criterios estructurados derivados y persistidos
- Evolucion de `Application` con:
  - `status`
  - `created_at`
  - `updated_at`
  - `problem_understanding`
  - `proposed_solution`
  - `capabilities_evidence`
  - `execution_plan`
  - borradores persistidos privados del postulante
  - promocion del mismo agregado de borrador a propuesta enviada
  - inmutabilidad post-envio
- Nuevo contexto `apps/evaluation/` con:
  - `AwardDecision`
  - historial del desafio
  - evaluacion por criterio
  - restriccion de completitud antes de adjudicar
  - ranking comparativo de propuestas con promedio por criterio
  - snapshot persistido de adjudicacion con contexto de ranking y excepcion
  - equipo formal de evaluacion con roles designados
- Nuevo contexto `apps/notifications/` con:
  - inbox interno
  - contador de no leidas
  - accion de marcar todas como leidas
- Eventos de dominio de evaluacion para:
  - inicio de evaluacion
  - evaluacion de propuesta
  - adjudicacion
- Consumers de eventos para:
  - timeline del desafio
  - notificaciones internas
- Resumenes agregados de evaluacion por propuesta visibles en:
  - detalle del desafio
  - pantalla de adjudicacion
- Politica aprobada e implementada de scoring y adjudicacion en:
  - `docs/domain/evaluation_scoring_and_award_policy.md`
- Endurecimiento operativo inicial con:
  - aislamiento de tests frente al `.env` local mediante `READ_DOT_ENV_FILE`
  - optimizacion de las suites mas costosas usando `setUpTestData()` en lugar de recrear el mismo grafo de datos por prueba
  - `Makefile` con comandos de validacion rapida y reproducible
  - `gunicorn` como servidor en `Dockerfile` y `docker-compose.yml`
- Sincronizacion de documentacion principal con el estado real del codigo.
- Cierre completo de la separacion tactica minima de `marketplace` sin romper el app fisico.
- Cierre completo del slice actual de convergencia semantica entre marketplace, evaluation y la documentacion principal.
- Plan rector v1 y ADRs de release:
  - `docs/release_plan_v1.md`
  - `docs/adr/0004-dual-mode-deployment.md`
  - `docs/adr/0005-multi-representative-onboarding.md`
  - `docs/adr/0006-attachments-and-markdown-content.md`
  - `docs/adr/0007-closed-challenge-taxonomy.md`
  - `docs/adr/0008-pilot-launch-posture.md`
  - `docs/adr/0009-accepted-release-risks.md`
- Onboarding multi-representante y gobierno organizacional inicial:
  - representante titular por organizacion
  - solicitudes de union con estados `PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`
  - aprobacion/rechazo por titular
  - expiracion mediante comando de management
  - transferencia de titularidad
- Hardening minimo de signup:
  - aceptacion versionada de terminos y politica de datos
  - verificacion de email por token
  - recuperacion de contrasena
  - Turnstile configurable
- Enriquecimiento de contenido y discovery:
  - categorias cerradas de desafio
  - seed de categorias
  - busqueda textual
  - filtros por categoria y estado
  - markdown sanitizado con `markdown` y `bleach`
  - adjuntos para desafio y propuesta con MIME allowlist e identificadores opacos
- Operacion de piloto:
  - `DEPLOYMENT_PROFILE`
  - `docker-compose.pilot.yml`
  - `docker-compose.production.yml`
  - dashboard minimo de administracion de plataforma

## Estado funcional actual

Hoy el sistema ya cubre de forma coherente estos flujos:

- registro unificado de usuario y organizacion
- registro de nuevos representantes sobre organizaciones existentes mediante solicitud de union
- aprobacion/rechazo de solicitudes de union por representante titular
- verificacion de email
- aceptacion versionada de terminos y politica de datos
- login y logout
- recuperacion de contrasena
- landing publica
- publicacion de desafios por organizaciones `Solicitante`
- categorizacion de desafios
- busqueda y filtros de desafios por texto, categoria y estado
- postulacion de propuestas por organizaciones `Proveedor tecnologico`
- guardado de borradores privados y reanudacion del mismo borrador desde la misma ruta de postulacion
- validacion de duplicados por desafio/aplicante
- adjuntos controlados en desafios y propuestas
- markdown sanitizado en descripcion de desafio y componentes de propuesta
- visualizacion de logos/avatares en marketplace
- separacion interna clara entre concern de publicacion de desafios y concern de postulacion de propuestas
- ciclo de vida de desafios con apertura, evaluacion y adjudicacion
- definicion y visualizacion de criterios de evaluacion
- evaluacion de propuestas criterio por criterio
- evaluacion ciega hasta adjudicar
- multiples evaluadores por criterio con agregacion por promedio del criterio
- ranking comparativo entre propuestas durante evaluacion y adjudicacion
- separacion entre propuestas competitivas y propuestas no elegibles aun
- empates tecnicos visibles con posicion compacta compartida
- adjudicacion de una propuesta ganadora
- adjudicacion excepcional auditada fuera del mejor lugar disponible
- snapshot de evaluacion conservado en la adjudicacion
- historial de evaluacion del desafio
- notificaciones internas disparadas por eventos de evaluacion
- notificacion al proveedor cuando su propuesta recibe una evaluacion
- notificaciones al equipo de evaluacion cuando se registra actividad de scoring
- dashboard minimo de administracion de plataforma con KPIs de piloto
- paginas publicas base de FAQ, terminos y politica de datos

## Estado tecnico actual

- `manage.py check`: OK
- `manage.py test`: OK
- suite actual validada: 109 tests
- validacion focal de esta sesion: 62 tests OK en `apps.identity.tests apps.marketplace.tests apps.notifications.tests`
- `manage.py check --deploy` con `DEPLOYMENT_PROFILE=production`: OK, sin issues
- benchmark actual de pruebas:
  - secuencial: `56.357s`
  - benchmark historico `--parallel 2`: `32.090s`
  - mejor benchmark historico `--parallel 4`: `30.723s`
  - validacion completa mas reciente `--parallel 4`: `38.974s`
- baseline historica previa a la optimizacion de fixtures: `396.022s`
- comando rapido recomendado para validacion local: `make test-fast`
- comando rapido recomendado para checklist completo: `make verify-fast`
- migraciones nuevas relevantes ya integradas en la iteracion:
  - `apps/marketplace/migrations/0004_challenge_application_deadline_challenge_status.py`
  - `apps/marketplace/migrations/0005_application_capabilities_evidence_and_more.py`
  - `apps/marketplace/migrations/0006_challenge_evaluation_criteria.py`
  - `apps/marketplace/migrations/0007_challengeevaluationcriterion.py`
  - `apps/marketplace/migrations/0008_application_lifecycle.py`
  - `apps/evaluation/migrations/0001_initial.py`
  - `apps/evaluation/migrations/0002_challengetimelineentry.py`
  - `apps/evaluation/migrations/0003_applicationcriterionevaluation.py`
  - `apps/evaluation/migrations/0004_awarddecision_evaluation_snapshot.py`
  - `apps/evaluation/migrations/0005_alter_challengetimelineentry_event_type.py`
  - `apps/evaluation/migrations/0006_challengeevaluationroleassignment.py`
  - `apps/evaluation/migrations/0007_multiple_evaluators_and_snapshot_counts.py`
  - `apps/evaluation/migrations/0008_awarddecision_best_available_applications_snapshot_and_more.py`
  - `apps/notifications/migrations/0001_initial.py`
  - `apps/notifications/migrations/0002_alter_notification_kind.py`
  - `apps/identity/migrations/0003_organizationjoinrequest_and_more.py`
  - `apps/identity/migrations/0004_emailverificationtoken.py`
  - `apps/marketplace/migrations/0009_challengecategory_applicationattachment_and_more.py`
- documentacion de dominio disponible en `docs/`
- servidor de desarrollo: no levantado en este momento
- base local ya sincronizada con las migraciones actuales

Nota:

- La referencia historica de coverage ya no debe tomarse como foto vigente; el sistema y la suite cambiaron de forma material durante esta iteracion.

## Artefactos relevantes de la iteracion

La iteracion actual incluye, entre otros:

- `docs/` con ontologia canonica v4, plan DDD, glosario, context map, invariantes, ADRs y plantilla
- `apps/marketplace/domain/`
- `apps/marketplace/challenge_forms.py`
- `apps/marketplace/application_forms.py`
- `apps/marketplace/challenge_views.py`
- `apps/marketplace/application_views.py`
- `apps/marketplace/content.py`
- `apps/marketplace/management/commands/seed_categories.py`
- `apps/identity/management/commands/expire_join_requests.py`
- `apps/evaluation/`
- `apps/notifications/`
- `config/admin_views.py`
- `config/context_processors.py`
- `docker-compose.pilot.yml`
- `docker-compose.production.yml`
- migraciones nuevas de `marketplace`, `evaluation` y `notifications`
- templates nuevas para evaluacion y notificaciones
- templates nuevas de legal, ayuda, verificacion de email, recuperacion de contrasena y solicitudes de union
- sincronizacion de `README.md`, `status_de_desarrollo.md` y este resumen ejecutivo
- `Makefile` con flujo de validacion rapida

## Limitaciones vigentes

Aunque el salto de calidad fue importante, todavia hay limites claros:

- el proyecto sigue en perfil de desarrollo
- ya existe perfil `pilot`/`production`, pero falta ejecutar despliegue real y smoke test en VPS
- SQLite sigue siendo la base por defecto
- Turnstile y SMTP dependen de credenciales reales de entorno; la validacion local no prueba integracion externa real
- los adjuntos usan filesystem local; la estrategia de backup sigue aceptada como riesgo para piloto
- aunque los eventos ya son mas utiles, la estrategia sigue concentrada sobre `Evaluation`
- ya existe evaluacion ciega en los flujos publisher-facing de evaluacion y adjudicacion
- ya existe un modelo de multiples evaluadores por criterio, con una evaluacion vigente por `(propuesta, criterio, evaluador)`
- todos los criterios tienen hoy el mismo valor; no existe ponderacion y esa es una decision activa de producto
- los borradores de propuesta ya existen como lifecycle persistido, pero siguen siendo deliberadamente privados y fuera de evaluacion hasta el envio final
- la adjudicacion ya es funcional y trazable, pero sigue siendo minima en gobierno avanzado de evaluacion
- `apps/marketplace/` sigue siendo un app fisico compartido, aunque su separacion tactica interna ya no depende de buckets genericos
- no se recalculo una metrica global de coverage actualizada
- el paralelismo optimo depende del host y de la forma actual de la suite; hoy sigue habiendo evidencia de que `--parallel` mejora claramente sobre el modo secuencial, pero conviene rebenchmarkear antes de afirmar que `4` siempre gana a `2`

## Conclusiones

La conclusion correcta ya no es "falta descubrir el dominio". La conclusion correcta hoy es: el dominio central ya esta bastante mas descubierto y una porcion relevante ya fue traducida al software ejecutable.

VIMER ya tiene:

- lenguaje ubicuo mas claro
- invariantes mas visibles
- bounded contexts mas explicitados
- flujo central del marketplace cerrado de punta a punta
- separacion tactica interna suficiente para evolucionar challenge y application con ownership mas claro
- eventos de dominio utiles en el ciclo de evaluacion
- read models simples pero valiosos para la toma de decision
- una politica de scoring y adjudicacion ya implementada y trazable de punta a punta

El proyecto todavia no esta listo para produccion, pero ya esta claramente por encima de una baseline CRUD: ahora tiene una base arquitectonica y semantica mucho mas apta para seguir iterando con disciplina.

Tambien quedo en una posicion operativa mucho mejor para iterar: la suite automatizada paso de una referencia historica de `396.022s` a una validacion final reciente de `38.974s` en corrida paralela completa, manteniendo como mejor benchmark medido `30.723s`, sin reducir cobertura funcional ni bajar el nivel de validacion.

## Siguiente paso recomendado

El siguiente bloque natural de implementacion deberia ir por uno de estos caminos:

1. profundizar `Evaluation`:
   - decisiones mejor gobernadas por actor y responsabilidad
   - auditoria y gobierno mas ricos sobre adjudicaciones excepcionales y empates
2. profundizar consumidores de eventos:
   - mas notificaciones
   - auditoria
   - timeline mas rico
3. cierre operativo del piloto v1:
   - VPS
   - TLS
   - SMTP real
   - Turnstile real
   - smoke test
   - monitoreo externo

La recomendacion actual cambia por prioridad de release: antes de profundizar `Evaluation`, conviene cerrar la validacion operativa del piloto v1. El faltante inmediato ya no es descubrir nuevas reglas de dominio, sino comprobar que el flujo completo opera con infraestructura, email, Turnstile, documentos legales y adjuntos bajo condiciones reales.
