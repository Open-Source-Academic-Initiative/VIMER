# Resumen Ejecutivo - VIMER

Fecha: 2026-03-26
Rama de trabajo: `baseline-iteration`

## Estado general

VIMER ya no esta solo en una baseline funcional de Django. En la iteracion actual se consolido una base de dominio mucho mas explicita, se reforzo el flujo principal del marketplace y se abrio un cierre minimo pero real del ciclo `Desafio -> Propuesta -> Evaluacion -> Adjudicacion`.

La fotografia correcta hoy es esta:

- El MVP sigue siendo navegable, estable y verificable.
- El proyecto ya cuenta con documentacion versionada de dominio en `docs/`.
- La ontologia canonica versionada del proyecto ahora vive en `docs/domain/ontology_v4.md`.
- El write-side principal ya no depende solo de vistas y forms; ahora se apoya en servicios de aplicacion explicitos.
- `Challenge` ya expresa estado, fecha limite y criterios de evaluacion.
- Los criterios de evaluacion ya no viven solo como texto libre; tambien existen como entradas estructuradas persistidas por desafio.
- `Application` ya funciona como una propuesta estructurada con componentes obligatorios e inmutabilidad post-envio.
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
- El proceso de evaluacion ya no depende de permisos implicitos por pertenecer a la organizacion publicadora: ahora existe un equipo formal con evaluadores designados, un adjudicador designado y observadores.
- El proyecto sigue sin estar listo para produccion.

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
  - `problem_understanding`
  - `proposed_solution`
  - `capabilities_evidence`
  - `execution_plan`
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

## Estado funcional actual

Hoy el sistema ya cubre de forma coherente estos flujos:

- registro unificado de usuario y organizacion
- login y logout
- landing publica
- publicacion de desafios por organizaciones `Solicitante`
- postulacion de propuestas por organizaciones `Proveedor tecnologico`
- validacion de duplicados por desafio/aplicante
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

## Estado tecnico actual

- `manage.py check`: OK
- `manage.py test`: OK
- suite actual validada: 99 tests
- benchmark actual de pruebas:
  - secuencial: `56.357s`
  - paralelo `--parallel 2`: `32.090s`
  - paralelo `--parallel 4`: `31.696s` en la validacion final mas reciente
- mejor benchmark historico paralelo medido en esta maquina: `30.723s`
- baseline historica previa a la optimizacion de fixtures: `396.022s`
- comando rapido recomendado para validacion local: `make test-fast`
- comando rapido recomendado para checklist completo: `make verify-fast`
- migraciones nuevas relevantes ya integradas en la iteracion:
  - `apps/marketplace/migrations/0004_challenge_application_deadline_challenge_status.py`
  - `apps/marketplace/migrations/0005_application_capabilities_evidence_and_more.py`
  - `apps/marketplace/migrations/0006_challenge_evaluation_criteria.py`
  - `apps/marketplace/migrations/0007_challengeevaluationcriterion.py`
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
- `apps/evaluation/`
- `apps/notifications/`
- migraciones nuevas de `marketplace`, `evaluation` y `notifications`
- templates nuevas para evaluacion y notificaciones
- sincronizacion de `README.md`, `status_de_desarrollo.md` y este resumen ejecutivo
- `Makefile` con flujo de validacion rapida

## Limitaciones vigentes

Aunque el salto de calidad fue importante, todavia hay limites claros:

- el proyecto sigue en perfil de desarrollo
- no existe aun un endurecimiento serio de despliegue/produccion
- SQLite sigue siendo la base por defecto
- aunque los eventos ya son mas utiles, la estrategia sigue concentrada sobre `Evaluation`
- ya existe evaluacion ciega en los flujos publisher-facing de evaluacion y adjudicacion
- ya existe un modelo de multiples evaluadores por criterio, con una evaluacion vigente por `(propuesta, criterio, evaluador)`
- todos los criterios tienen hoy el mismo valor; no existe ponderacion y esa es una decision activa de producto
- la adjudicacion ya es funcional y trazable, pero sigue siendo minima en gobierno avanzado de evaluacion
- `apps/marketplace/` sigue siendo un app fisico compartido, aunque su separacion tactica interna ya no depende de buckets genericos
- no se recalculo una metrica global de coverage actualizada
- el paralelismo optimo depende del host; en esta maquina `--parallel 4` fue levemente mejor que `--parallel 2`

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

Tambien quedo en una posicion operativa mucho mejor para iterar: la suite automatizada paso de una referencia historica de `396.022s` a una validacion final reciente de `31.696s` en corrida paralela completa, manteniendo como mejor benchmark medido `30.723s`, sin reducir cobertura funcional ni bajar el nivel de validacion.

## Siguiente paso recomendado

El siguiente bloque natural de implementacion deberia ir por uno de estos caminos:

1. profundizar `Evaluation`:
   - decisiones mejor gobernadas por actor y responsabilidad
   - auditoria y gobierno mas ricos sobre adjudicaciones excepcionales y empates
2. profundizar consumidores de eventos:
   - mas notificaciones
   - auditoria
   - timeline mas rico
3. endurecimiento operativo:
   - despliegue
   - seguridad
   - configuracion productiva

La recomendacion actual es continuar primero por `Evaluation`, y el siguiente faltante funcional real ya no es la separacion tactica minima de `marketplace`, el ranking, la trazabilidad basica, los roles formales, la evaluacion ciega ni la politica de scoring. El siguiente faltante real pasa a ser mejor gobierno de decisiones, auditoria mas rica y la definicion de si algun dia el producto necesitara ponderacion distinta entre criterios.
