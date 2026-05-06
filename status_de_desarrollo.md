# Status de Desarrollo - VIMER

Fecha de corte: 2026-05-05
Rama analizada: `main`

## 1. Alcance del analisis

Este documento resume el estado real del repositorio a partir de:

- Documentacion funcional y tecnica disponible en `README.md`.
- Documentacion de dominio versionada en `docs/domain/`.
- Estructura y codigo fuente de `config/`, `apps/` y `templates/`.
- Suite automatizada actual.
- Estado del repositorio Git y convenciones locales del workspace.
- Artefactos rectores actuales del dominio:
  - `docs/domain/ontology_v4.md`
  - `docs/domain/glossary.md`
  - `docs/domain/context_map.md`
  - `docs/domain/invariants.md`
  - ADRs y plantillas bajo `docs/`

No existe en el repositorio una especificacion formal separada de "requerimientos iniciales". Por eso, el cumplimiento se evalua contra los requisitos inferidos del MVP descritos en `README.md`, contra el comportamiento implementado en el codigo y contra el corpus de dominio versionado actual, cuyo documento canonico es `docs/domain/ontology_v4.md`.

## 2. Resumen ejecutivo

El proyecto se encuentra en una etapa de MVP funcional y navegable. La base tecnologica esta operativa, los flujos criticos de autenticacion y marketplace funcionan, existe una capa de servicios de aplicacion para los casos de uso de escritura mas importantes y, tras la sesion actual de modelado, ya existe un marco estrategico, tactico y ontologico mucho mas explicito para gobernar su evolucion.

El estado general puede resumirse asi:

- El MVP cumple el nucleo funcional esperado para una primera iteracion.
- La navegacion publica ya no cae directamente en registro; existe una landing page inicial para separar el acceso publico del flujo autenticado.
- Las reglas de negocio principales estan implementadas y cubiertas al menos de forma basica por pruebas automatizadas.
- La terminologia de negocio visible al usuario ya fue alineada a `Solicitantes` y `Proveedores tecnologicos`.
- Existe una salvaguarda explicita en Django Admin para impedir que un superusuario se autoelimine.
- Los desafios ya incluyen criterios de evaluacion explicitos y no pueden pasar a evaluacion sin esa base semantica.
- Los criterios de evaluacion ya no viven solo como texto libre: ahora pueden materializarse como entradas estructuradas por desafio.
- La evaluacion ya no depende solo de adjudicacion final: ahora admite evaluaciones parciales por criterio sobre cada propuesta.
- La decision de adjudicacion ya no depende de lectura dispersa de comentarios: ahora existen resumenes agregados por propuesta para comparar avance, puntaje, promedio y ranking.
- El scoring ya no depende del volumen bruto de evaluaciones registradas: ahora promedia por criterio y mantiene el mismo valor para todos los criterios.
- La adjudicacion ahora conserva un snapshot del estado de evaluacion de la propuesta ganadora al momento de decidir, incluyendo contexto de mejor posicion disponible, empates y adjudicaciones excepcionales.
- La evaluacion por criterios ya emite un evento explicito, que alimenta timeline y notificaciones al postulante evaluado.
- La adjudicacion se bloquea mientras existan propuestas activas con criterios pendientes de evaluacion.
- Los empates tecnicos ya quedan visibles con posicion compacta compartida y resolucion humana por adjudicador.
- La adjudicacion excepcional fuera del mejor lugar disponible ya esta implementada y requiere confirmacion, motivo estructurado y justificacion obligatoria.
- `apps/marketplace/` ya no depende de buckets genericos para challenge y application: la separacion tactica interna ya existe tambien en forms, views, consumo de urls y pruebas.
- El cierre previsto de Fase 6 ya quedo ejecutado en el alcance actual: marketplace y evaluation usan mejor el lenguaje ubicuo en UI visible, pruebas de negocio y documentos principales.
- La suite ya no depende por defecto del `.env` del workspace para correr pruebas.
- El proyecto ya adopta varias capacidades concretas de Django 6.0 en el codigo real: `STORAGES`, CSP nativa mediante `ContentSecurityPolicyMiddleware` y `SECURE_CSP`, `ASGI_APPLICATION`, `manage.py check --deploy` y serving con `gunicorn`.
- La alineacion con Django 6.0 sigue siendo parcial en seguridad avanzada: la CSP todavia permite inline script/style por compatibilidad con templates existentes, y las capacidades nuevas de template partials y Tasks framework no se usan aun porque el producto todavia no las necesita.
- La estrategia de serving en contenedores ya no depende de `runserver`; ahora usa `gunicorn`.
- El proceso de evaluacion ya no depende solo de pertenecer a la organizacion publicadora: ahora existe un equipo formal con evaluadores designados, un adjudicador designado y observadores.
- La sesion actual movio el proyecto desde "MVP con arquitectura explicita" hacia un release v1 de piloto cerrado: existe `docs/release_plan_v1.md`, ADRs 0004-0009, perfiles `pilot`/`production`, compose files diferenciados y una primera implementacion de los flujos v1 mas criticos.
- `Identity` ya soporta onboarding multi-representante con representante titular, solicitudes de union a organizacion, aprobacion/rechazo por titular, expiracion por comando, transferencia de titularidad, verificacion de correo, aceptacion versionada de documentos legales y Turnstile configurable.
- `Marketplace` ya soporta categorias cerradas, busqueda/filtros en el listado, markdown sanitizado en contenido largo y adjuntos PDF/JPG/PNG para desafios y propuestas mediante identificadores opacos y vistas de descarga con permisos.
- Ya existe un dashboard minimo de administracion de plataforma en `/admin/dashboard/` con KPIs de piloto.
- Ya existen paginas publicas base de ayuda/legal y enlaces de soporte en la UI.
- `DEPLOYMENT_PROFILE=production` valida con `manage.py check --deploy` sin issues cuando se proveen las variables requeridas.
- El proyecto ya no depende solo de DDD implicito en el codigo: ahora existe un corpus versionado con context map, lenguaje ubicuo, inventario de invariantes y una ontologia canonica v4 con entidades, actores, roles, permisos, estados, eventos e invariantes.
- El proyecto no esta listo para produccion general todavia, pero ya tiene una postura de piloto cerrado mucho mas concreta.

## 2.1 Cambios y acciones ejecutadas en la sesion 2026-05-05

Durante esta sesion se consolidaron cambios de producto, arquitectura, operacion y documentacion orientados al primer release controlado:

- Se creo `docs/release_plan_v1.md` como plan rector del piloto cerrado v1.
- Se agregaron ADRs 0004-0009 para despliegue dual, onboarding multi-representante, adjuntos/markdown, taxonomia cerrada, postura de piloto y riesgos aceptados.
- Se extendio `Identity` con `OrganizationJoinRequest`, estados de cuenta, titularidad de organizacion, verificacion de email, aceptacion legal versionada, Turnstile configurable y vistas para aprobar/rechazar solicitudes de union.
- Se agrego el comando `expire_join_requests` para expirar solicitudes pendientes.
- Se extendio `Marketplace` con `ChallengeCategory`, `ChallengeAttachment`, `ApplicationAttachment`, markdown sanitizado con `markdown`/`bleach`, busqueda por texto, filtros por categoria/estado y comando `seed_categories`.
- Se agregaron permisos de descarga para adjuntos de desafio y propuesta, respetando el flujo de evaluacion ciega donde aplica.
- Se agregaron plantillas legales, FAQ, paginas de recuperacion de contrasena, verificacion de correo y administracion de solicitudes de union.
- Se agrego `config/admin_views.py` con dashboard minimo de administracion de plataforma y ruta `/admin/dashboard/`.
- Se introdujo `DEPLOYMENT_PROFILE` en settings, junto con `docker-compose.pilot.yml`, `docker-compose.production.yml` y artefactos base bajo `deploy/`.
- Se actualizaron `README.md`, `docs/ddd_work_plan.md`, `docs/domain/context_map.md`, `docs/domain/glossary.md`, `docs/domain/invariants.md` y `docs/domain/ontology_v4.md` para reflejar el alcance v1.
- Se ejecuto validacion focal: `READ_DOT_ENV_FILE=False SECRET_KEY=dev-secret-key ./.venv/bin/python manage.py test apps.identity.tests apps.marketplace.tests apps.notifications.tests` con 62 tests OK.
- Se ejecuto validacion de despliegue: `DEPLOYMENT_PROFILE=production DATABASE_URL=sqlite:////tmp/vimer-check.sqlite3 ... manage.py check --deploy` sin issues.

## 3. Grado de cumplimiento de requerimientos iniciales

### 3.1 Requerimiento: registro de usuario y organizacion

Estado: Cumplido y ampliado para piloto v1

Evidencia:

- Existe un flujo de registro unificado para usuario y organizacion.
- Se capturan datos de organizacion, credenciales y telefono de contacto.
- Se permite subir un logo personalizado de la organizacion durante el registro, restringido a PNG o JPG.
- Si no se sube imagen, el sistema genera automaticamente un avatar procedural basico en PNG.
- La unicidad del NIT se valida.
- La contrasena se valida con el sistema de validadores de Django.
- Si el NIT ya existe, el nuevo usuario no crea una organizacion duplicada; queda como representante pendiente y se crea una solicitud de union a la organizacion existente.
- El primer usuario de una organizacion queda como representante titular.
- El registro persiste aceptacion de terminos y politica de datos por version.
- El registro puede exigir Turnstile si se configura `TURNSTILE_SECRET_KEY`.
- El registro dispara token de verificacion de email.

Valoracion:

- El requerimiento principal esta resuelto.
- La implementacion ya no persiste directamente desde la vista; delega en un servicio de aplicacion.
- El flujo ya cubre una necesidad operativa real del piloto: multiples representantes por organizacion sin compartir credenciales.

### 3.2 Requerimiento: autenticacion basica

Estado: Cumplido y ampliado

Evidencia:

- Existe login y logout.
- El logout se maneja por `POST`, lo cual corrige el comportamiento previo menos seguro basado en `GET`.
- El marketplace exige autenticacion.
- Existen vistas y plantillas para recuperacion de contrasena.
- Existe verificacion de email mediante token.

Valoracion:

- El comportamiento esperado para un MVP esta cubierto.

### 3.3 Requerimiento: gestion de roles de negocio

Estado: Cumplido con observaciones y gobierno organizacional inicial

Evidencia:

- El modelo `Organization` define dos roles persistidos: `DEMAND_SIDE` y `SUPPLY_SIDE`.
- La semantica visible al usuario se presenta como `Solicitante` y `Proveedor tecnologico`.
- La navegacion y los permisos de publicacion/postulacion dependen del rol.
- El modelo `User` ahora distingue estado de cuenta, correo verificado y representante titular.
- La aprobacion/rechazo de nuevas solicitudes de union queda restringida al representante titular activo.

Observaciones:

- A nivel tecnico, los codigos internos siguen siendo `DEMAND_SIDE` y `SUPPLY_SIDE`, lo cual es correcto para no romper datos existentes.
- A nivel documental, el `README.md` principal ya fue sincronizado, pero esa consistencia debe mantenerse como disciplina continua y no como correccion puntual.

### 3.4 Requerimiento: publicacion de desafios por organizaciones solicitantes

Estado: Cumplido

Evidencia:

- Existe vista, formulario y plantilla para crear desafios.
- Solo organizaciones con rol `Solicitante` pueden publicarlos.
- La validacion ocurre tanto en la capa de interfaz como en el modelo.
- La publicacion ya captura criterios de evaluacion como parte del desafio.

Valoracion:

- Este requisito esta efectivamente implementado para el MVP.

### 3.5 Requerimiento: consulta de desafios y detalle

Estado: Cumplido y ampliado

Evidencia:

- Existe listado autenticado de desafios.
- Existe vista detalle con descripcion completa.
- La UI ya permite revisar desafios como usuario autenticado segun rol.
- El listado ya permite busqueda textual y filtros por categoria y estado.
- Los desafios ya pueden clasificarse por una taxonomia cerrada de categorias activas.
- La descripcion puede renderizar markdown sanitizado.

Valoracion:

- Cumple el objetivo funcional esperado.

### 3.6 Requerimiento: postulacion de propuestas por proveedores tecnologicos

Estado: Cumplido y ampliado

Evidencia:

- Existe vista, formulario y caso de uso para postular a un desafio.
- Solo organizaciones con rol `Proveedor tecnologico` pueden aplicar.
- No se permite duplicar postulaciones para un mismo desafio.
- La misma ruta de postulacion ya permite guardar borrador o enviar propuesta final.
- Si existe un borrador previo, la misma ruta lo reabre y lo actualiza.
- Los borradores permanecen privados y no entran en evaluacion ni en vistas publisher-facing hasta el envio final.
- Las propuestas ya pueden incluir adjuntos controlados.
- Los cuatro componentes largos de propuesta ya pueden renderizar markdown sanitizado.

Valoracion:

- El flujo esta implementado y probado.
- Ademas, ya existe lifecycle persistido de borrador para `Propuesta`, con reglas distintas para guardado parcial y envio final.

### 3.7 Requerimiento: area administrativa minima

Estado: Cumplido

Evidencia:

- Existe integracion con Django Admin para usuarios, organizaciones, desafios y postulaciones.

Valoracion:

- Suficiente para operacion basica de un MVP.

### 3.8 Requerimiento: superusuario / administrador de plataforma

Estado: Cumplido con observaciones

Evidencia:

- Existe integracion con Django Admin para usuarios, organizaciones, desafios y postulaciones.
- El proyecto ya utiliza el concepto tecnico de `superuser` provisto por Django para operacion administrativa.
- A nivel ontologico, este rol no pertenece al mercado de interaccion entre `Solicitantes` y `Proveedores tecnologicos`; pertenece a la capa de gobierno y operacion de la plataforma.
- Operativamente, el `Superusuario` / `Administrador de plataforma` debe ser el primer usuario creado en la plataforma para habilitar el gobierno inicial del sistema.

Capacidades definidas:

- Puede crear, actualizar/editar o eliminar cualquier usuario de la plataforma, incluyendo representantes de organizaciones `Solicitantes` y `Proveedores tecnologicos`.
- Puede crear, actualizar/editar o eliminar desafios publicados.

Restriccion definida:

- No puede eliminarse a si mismo.

Valoracion:

- La capacidad administrativa general ya existe de forma tecnica a traves de Django Admin y el uso de superusuario.
- La regla de negocio operativa que impide la autoeliminacion del superusuario ya aparece implementada como salvaguarda explicita en Django Admin.
- El alcance implementado actual es administrativo: protege el panel de administracion, incluyendo la eliminacion individual y la accion masiva de borrado.
- Para mantener coherencia con principios de DDD, este rol debe modelarse como `Administrador de plataforma` o `Superusuario`, separado del lenguaje ubicuo del dominio de mercado y sin mezclarlo con los roles `Solicitante` y `Proveedor tecnologico`.
- La indicacion de que el superusuario debe ser el primer usuario creado en la plataforma sigue siendo una convencion operativa de bootstrap, no una invariante tecnica global impuesta por el modelo.

### 3.9 Requerimiento: contenedorizacion basica

Estado: Cumplido para piloto, parcial para produccion general

Evidencia:

- Existen `Dockerfile` y `docker-compose.yml`.
- La aplicacion puede levantarse en modo desarrollo.
- Existen `docker-compose.pilot.yml` y `docker-compose.production.yml`.
- `DEPLOYMENT_PROFILE` permite defaults coherentes para `pilot` y `production`.

Limitacion:

- La topologia de produccion esta definida, pero aun requiere validacion operativa real en VPS, TLS, monitoreo externo y datos reales de entorno.

## 4. Requerimientos no cumplidos o solo parcialmente cubiertos

### 4.1 Produccion y endurecimiento operativo

Estado: Parcial, con postura v1 definida

Situacion actual:

- Existen settings orientados a seguridad para entornos no `DEBUG`.
- Se puede exigir `SECRET_KEY` y activar cookies seguras, HSTS y redireccion HTTPS.
- `DEPLOYMENT_PROFILE=production` exige `DATABASE_URL` y activa defaults seguros cuando `DEBUG=False`.
- `manage.py check --deploy` valida sin issues con perfil production y variables minimas requeridas.
- Existen compose files separados para piloto y produccion.

Brechas:

- El despliegue real no esta cerrado.
- Aunque ya existe `gunicorn` como servidor de aplicacion en contenedores y compose file de produccion, no hay despliegue productivo real validado.
- No hay pipeline operativo visible en el repo.
- Falta ejecutar y documentar una prueba real de despliegue sobre VPS.

### 4.2 Cobertura de pruebas

Estado: Parcial

Situacion actual:

- La suite automatizada pasa completamente con 109 pruebas.
- Hay cobertura de registro, validacion de NIT, contrasenas debiles, logout, landing page, publicacion/postulacion basica, errores de duplicado/rol, validacion de imagenes PNG/JPG, generacion procedural de avatar/logo, renderizado del logo en publicaciones del marketplace y proteccion del superusuario frente a autoeliminacion en admin.
- Ya hay cobertura adicional sobre scoring igualitario por criterio, ranking competitivo con empates compactos, bloqueo de adjudicacion por propuestas incompletas, adjudicacion excepcional auditada, snapshot enriquecido de adjudicacion, eventos de evaluacion por propuesta y notificaciones al proveedor evaluado.
- En esta sesion se valido el slice focal `apps.identity.tests apps.marketplace.tests apps.notifications.tests`: 62 tests OK en 52.609s.

Brechas:

- La cobertura sigue siendo pequena para el dominio total.
- Faltan pruebas negativas adicionales sobre permisos, errores de integracion, seguridad y casos de borde.

### 4.3 UX/UI y experiencia de producto

Estado: Parcial

Situacion actual:

- Ya existe landing page publica y diferenciacion basica de navegacion.
- Las pantallas principales son operables.

Brechas:

- La UI general sigue siendo sencilla y mayormente utilitaria.
- No hay sistema de estilos mas robusto, componentes reutilizables ni refinamiento visual profundo.

### 4.4 Documentacion operativa completamente sincronizada

Estado: Cumplido con observaciones

Situacion actual:

- Existe un `README.md` bastante completo y sincronizado con el estado actual de la iteracion local.
- Los documentos locales de apoyo tambien fueron actualizados para reflejar el conteo real de pruebas y el alcance actual del superusuario.
- `status_de_desarrollo.md` y `resumen_ejecutivo.md` ya forman parte del repositorio versionado y no deben tratarse como notas ignoradas del workspace.
- Durante sesiones previas se construyeron y consolidaron artefactos de modelado de dominio mas fuertes:
  - `docs/domain/ontology_v4.md` como ontologia canonica;
  - `docs/domain/glossary.md` como lenguaje ubicuo preferido;
  - `docs/domain/context_map.md` como mapa de bounded contexts;
  - `docs/domain/invariants.md` como inventario trazable de reglas.
- Durante esta sesion se agregaron artefactos rectores especificos para release v1:
  - `docs/release_plan_v1.md`;
  - `docs/adr/0004-dual-mode-deployment.md`;
  - `docs/adr/0005-multi-representative-onboarding.md`;
  - `docs/adr/0006-attachments-and-markdown-content.md`;
  - `docs/adr/0007-closed-challenge-taxonomy.md`;
  - `docs/adr/0008-pilot-launch-posture.md`;
  - `docs/adr/0009-accepted-release-risks.md`.

Brechas:

- Aun falta institucionalizar una disciplina de actualizacion documental por iteracion, para que README, ADRs, glosario, ontologia, reportes y decisiones de modelado evolucionen de forma coordinada.
- Aunque estos documentos ya estan versionados, pueden volver a desincronizarse si no se mantienen conscientemente junto al codigo y las migraciones.

## 5. Metodologias y buenas practicas aplicadas hasta el momento

### 5.1 Separacion de responsabilidades

Aplicada: Si

Descripcion:

- El proyecto separa configuracion, identidad, organizacion corporativa y marketplace por apps.
- El flujo de escritura no queda concentrado solo en forms o vistas.
- La logica de negocio principal se mueve a servicios de aplicacion.

Impacto:

- Mejora la mantenibilidad.
- Reduce acoplamiento entre capa web y reglas de negocio.

### 5.2 Enfoque DDD tactico y estrategico

Aplicada: Si, ahora de manera explicita a nivel documental y aun parcial a nivel de codigo

Descripcion:

- Ya no solo hay una aproximacion intuitiva a DDD: la sesion actual dejo un context map versionado y explicito dentro de `docs/domain/context_map.md`.
- Se distinguieron bounded contexts concretos:
  - `Identity`
  - `Corporate`
  - `Marketplace`
  - `Notifications`
  - `Administracion de plataforma`
- A nivel conceptual, `Marketplace` ya se lee internamente como dos subdominios: `Challenge` y `Application`.
- Esa separacion ya fue traducida de forma tactica al codigo mediante servicios, reglas, forms, views y pruebas diferenciadas por concern.
- Se formalizo el core domain como el ciclo `Desafio -> Propuesta -> Evaluacion/Adjudicacion`.
- Se definieron agregados raiz concretos:
  - `Desafio`
  - `Propuesta`
  - `DecisionDeAdjudicacion`
- Se distinguio explicitamente entre servicios de aplicacion ya presentes y futuros servicios de dominio nombrados, como `ValidadorDeRolSolicitante`.

Impacto:

- La evolucion futura del sistema ya puede guiarse por limites de dominio y no solo por conveniencia tecnica.
- Se reduce el riesgo de seguir creciendo el modulo `marketplace` como contenedor ambiguo.
- Queda una base clara para refactorizar el codigo hacia DDD tactico real sin redescubrir el negocio en cada iteracion.

### 5.3 Validacion multicapa

Aplicada: Si

Descripcion:

- Se validan formularios.
- Se validan modelos via `full_clean()`.
- Existen restricciones a nivel de base de datos, como la unicidad de postulacion por desafio y aplicante.
- Tras la sesion de modelado, las reglas ya no son solo validaciones dispersas: quedaron formalizadas como invariantes de dominio versionadas y trazables en `docs/domain/invariants.md`.

Impacto:

- Refuerza consistencia de datos.
- Reduce el riesgo de inconsistencias por errores en una sola capa.
- Abre la puerta a migrar de "validaciones ad hoc" a enforcement deliberado por agregado, servicio de dominio y constraint persistente donde corresponda.

### 5.4 Lenguaje ubicuo gobernado

Aplicada: Si, a nivel documental y de criterio de revision

Descripcion:

- Se consolidaron terminos canonicos no negociables:
  - `Desafio`
  - `Propuesta`
  - `Solicitante`
  - `Proveedor tecnologico`
  - `Representante`
  - `Administracion de plataforma`
- Se declararon aliases eliminados que no deben reaparecer en UI, tests, documentacion ni conversaciones de dominio.
- Se acepto explicitamente que `Challenge` y `Application` sobreviven por ahora solo como deuda tecnica nombrada en persistencia y modulos Django.
- Se adopto una regla de revision: si un PR introduce aliases eliminados en codigo visible al usuario, pruebas o documentacion nueva, debe rechazarse en ese punto.

Impacto:

- Baja el costo futuro de limpieza semantica.
- Aumenta la consistencia entre negocio, UI, pruebas y codigo.
- Reduce especialmente la colision semantica entre `Application` como modelo tecnico y `application layer` como capa arquitectonica.

### 5.5 Pruebas automatizadas

Aplicada: Si

Descripcion:

- Se usan pruebas con `django.test.TestCase`.
- Se cubren flujos web y servicios de aplicacion.
- Se agregaron pruebas de regresion sobre bugs corregidos.

Impacto:

- Mejora la confianza al refactorizar.
- Permite validar cambios semanticos y de navegacion.

### 5.6 Correccion incremental guiada por evidencia

Aplicada: Si

Descripcion:

- Se identificaron problemas reales a partir del comportamiento observado.
- Se corrigieron con cambios pequenos, enfocados y luego cubiertos por pruebas.

Ejemplos:

- correccion del logout por `POST`;
- correccion del manejo semantico de errores en postulaciones;
- introduccion de landing page para separar navegacion publica y registro.

### 5.7 Compatibilidad de configuracion por entorno

Aplicada: Si

Descripcion:

- Se usa `django-environ`.
- Se diferencian comportamientos de desarrollo y no desarrollo.
- La base puede cambiar via `DATABASE_URL`.

Impacto:

- Buena base para escalar a otros entornos.

### 5.8 Ontologia formal del dominio

Aplicada: Si, a nivel documental y ya parcialmente traducida a enforcement ejecutable

Descripcion:

- Se formalizo una ontologia canonica versionada (`ontology_v4.md`) que separa explicitamente:
  - entidades;
  - actores;
  - roles;
  - permisos;
  - estados;
  - eventos de dominio;
  - invariantes;
  - relaciones semanticas.
- Ya no se mezclan de forma ambigua conceptos como actor humano, rol de mercado, rol en contexto, permiso y mecanismo tecnico.
- En la sesion actual se extendio la ontologia y el inventario de invariantes con conceptos de release v1: representante titular, solicitud de union, aceptacion legal, categorias, adjuntos, markdown sanitizado, Turnstile y postura de piloto.
- Se asignaron cardinalidades a relaciones clave del dominio, por ejemplo:
  - una `Organizacion` adopta exactamente un rol de mercado;
  - un `Proveedor tecnologico` envia como maximo una `Propuesta` por `Desafio`;
  - una `DecisionDeAdjudicacion` selecciona como maximo una `Propuesta` ganadora.

Impacto:

- Aumenta de forma significativa la alineacion conceptual con DDD y ontologias.
- Permite usar el dominio como artefacto gobernable y no solo como narracion descriptiva.
- Hace posible trazar reglas, permisos y eventos desde negocio hasta pruebas e implementacion.

### 5.9 Seguridad basica de framework

Aplicada: Si, parcialmente

Descripcion:

- `CsrfViewMiddleware` activo.
- Password validators activos.
- Opciones de cookies seguras y HSTS parametrizadas por entorno.
- `X_FRAME_OPTIONS` configurado.

Limite:

- Esto no equivale a hardening completo de produccion.

### 5.10 Control de versiones y trabajo por ramas

Aplicada: Si

Descripcion:

- El trabajo reciente esta actualmente en la rama `main` del workspace local.
- Hay cambios amplios pendientes de commit que conviene agrupar cuidadosamente antes de integrar historial.
- Existen archivos locales y operativos fuera de Git gracias a `.gitignore`.

Impacto:

- Permite iterar sin contaminar el historial principal.

## 6. Estado actual de alineacion DDD y ontologica

Las sesiones recientes cambiaron de manera importante el punto de partida del proyecto. Antes del ejercicio de modelado, VIMER mostraba intuiciones sanas de DDD en el codigo, pero sin artefactos formales suficientes para gobernar el dominio. Despues de ese trabajo y de la consolidacion v1, el estado correcto ya no es "DDD ligero e implicito", sino "modelo de dominio formalizado documentalmente, parcialmente implementado en codigo y orientado a un piloto cerrado verificable".

### 6.1 Logros de alineacion ya consolidados

- Existe una definicion explicita del core domain:
  - `Challenge`
  - `Application`
  - `Evaluation`
- Existe un context map versionado con bounded contexts y relaciones de integracion:
  - `Identity`
  - `Corporate`
  - `Marketplace`
  - `Evaluation`
  - `Notifications`
  - `Administracion de plataforma`
- El lenguaje ubicuo ya no es solo una preferencia editorial: quedaron fijados terminos canonicos y aliases eliminados.
- Se definieron agregados raiz y componentes tacticos:
  - `Desafio`
  - `Propuesta`
  - `DecisionDeAdjudicacion`
- Se definieron ciclos de vida objetivos para `Desafio` y `Propuesta`.
- Se formalizaron e implementaron primeros eventos de dominio explicitos en `Evaluation`, junto con un historial persistente de evaluacion.
- Existe un inventario de invariantes versionado y parcialmente reflejado en codigo y pruebas.
- Existe una ontologia canonica v4 con separacion entre entidades, actores, roles, permisos, estados, eventos, invariantes y relaciones semanticas.

### 6.2 Brecha restante entre modelo y codigo

- La evaluacion ciega ya existe en query models, vistas y templates publisher-facing, y la identidad del postulante solo se revela al adjudicar.
- Los roles formales de evaluacion ya existen en el software, y el modelo multi-evaluador por criterio tambien ya fue traducido al codigo ejecutable.
- La politica aprobada de scoring igualitario, ranking con empates visibles y adjudicacion excepcional gobernada ya fue traducida al codigo ejecutable.
- El lifecycle persistido `DRAFT -> SUBMITTED` para `Propuesta` ya fue traducido al codigo ejecutable y permanece privado al postulante hasta el envio final.
- El split tactico de `marketplace` ya existe internamente en servicios, reglas, forms, views y pruebas, aunque no como separacion fisica de apps Django.
- El copy visible de marketplace y evaluation, junto con las pruebas de negocio de ambos subdominios, ya reflejan el lenguaje ubicuo canonico de `Desafio` y `Propuesta`.
- La convergencia semantica prevista para esta fase ya no aparece solo como direccion editorial: quedo reflejada en pantallas visibles, nombres de suites de negocio y documentos rectores.
- `CriterioDeEvaluacion` ya existe en forma implementada como criterio estructurado por desafio, pero aun no esta plenamente alineado con el lenguaje canonico del modelo.
- `Challenge` y `Application` siguen siendo nombres tecnicos heredados en persistencia y modulos Django.
- La ontologia existe como artefacto documental, pero todavia no se refleja plenamente en nombres, APIs, vistas, validaciones e interfaces del codigo.

### 6.3 Nivel de alineacion por dimension

- DDD estrategico: alto a nivel documental, medio-alto a nivel implementado.
- DDD tactico: medio-alto a nivel documental, medio a nivel implementado.
- Lenguaje ubicuo: alto a nivel documental y de criterio de revision, medio en el codigo heredado.
- Ontologia formal: medio-alto a nivel documental, medio a nivel implementado.
- Gobierno metodologico: medio; ya existe una hoja de ruta mucho mas clara, pero aun no institucionalizada en ADRs, checklists y disciplina de iteracion.

## 7. Riesgos, deudas y puntos de atencion

### 7.1 Riesgo documental

- El `README.md` versionado esta alineado con el estado actual, y `status_de_desarrollo.md` junto con `resumen_ejecutivo.md` ya estan versionados tambien.
- Ahora el riesgo es mayor porque ya existe un corpus de dominio mas sofisticado: `README.md`, `docs/domain/*`, `status_de_desarrollo.md` y `resumen_ejecutivo.md` deben mantenerse coherentes entre si.
- Conviene mantener una rutina de sincronizacion documental por iteracion para evitar decisiones basadas en informacion vieja.

### 7.2 Riesgo operativo

- El entorno local sigue dependiendo de `.env` para desarrollo y despliegue local.
- Las pruebas ya no dependen por defecto del `.env` del workspace, pero el comportamiento de deploy sigue condicionado por la configuracion efectiva del entorno.
- La configuracion por `DEPLOYMENT_PROFILE` reduce ambiguedad entre piloto y produccion, pero todavia no sustituye una validacion real del stack en infraestructura.
- Aunque Django 6.0 ya ofrece CSP nativa y el proyecto la usa, la politica actual conserva `unsafe-inline` para script/style; eso debe endurecerse antes de considerar un perfil productivo serio.
- Django 6.0 tambien ofrece template partials y Tasks framework, pero hoy no hay un caso de producto que justifique adoptarlos y hacerlo antes de tiempo agregaria complejidad sin retorno claro.

### 7.3 Riesgo de cobertura

- El dominio esta mejor cubierto que al inicio, pero aun hay pocos escenarios automatizados comparados con los flujos posibles.
- Aun no existe una matriz clara de cobertura por invariante; la cobertura actual sigue estando mas cerca de flujos y regresiones que de una bateria deliberada por `INV-*`.

### 7.4 Riesgo semantico

- Si el codigo sigue creciendo sin adoptar los terminos canonicos y los nuevos limites de contexto, la deuda semantica volvera a crecer.
- El nombre tecnico `Application` sigue siendo especialmente riesgoso por su colision con `application layer`.

### 7.5 Riesgo de producto

- El MVP prueba el flujo, pero aun no resuelve una experiencia madura de onboarding, gestion de errores amigable ni administracion avanzada del ciclo de vida de desafios.
- El onboarding multi-representante ya mejora la operacion del piloto, pero todavia falta cerrar experiencia de transferencia de titularidad y administracion de excepciones mas alla del alcance minimo implementado.

## 8. Nivel actual de avance

Valoracion general del desarrollo:

- Entre 85% y 92% respecto al MVP funcional inferido.
- Entre 80% y 90% respecto a la formalizacion conceptual deseada en DDD y ontologias.
- Entre 65% y 75% respecto a la implementacion efectiva en codigo del modelo DDD/ontologico objetivo.
- Entre 60% y 70% respecto al release v1 de piloto cerrado definido en `docs/release_plan_v1.md`.

Interpretacion de esa estimacion:

- El nucleo funcional principal esta cubierto y el piloto v1 ya tiene varios prerequisitos implementados.
- La base tecnica es coherente y ahora distingue mejor entre perfil `pilot` y perfil `production`.
- La navegacion y el dominio ya se pueden probar manualmente.
- Ya no falta principalmente "descubrir el dominio"; eso quedo mucho mas avanzado en esta sesion.
- Lo que falta ahora es trasladar de manera disciplinada ese modelo al codigo, a las pruebas, a los nombres tecnicos y a la operacion del producto.

## 9. Recomendaciones prioritarias

1. Mantener `docs/domain/ontology_v4.md` como documento canónico único y sincronizar con él el resto del corpus de seguimiento.
2. Mantener `docs/release_plan_v1.md` como rector del piloto y actualizarlo junto con ADRs e invariantes cuando cambie el alcance.
3. Completar validacion end-to-end del release v1:
   - flujo real de signup con Turnstile;
   - verificacion de email con SMTP;
   - recuperacion de contrasena;
   - subida y descarga de adjuntos;
   - categorias y filtros;
   - dashboard admin;
   - despliegue en VPS.
4. Mantener la separacion tactica ya lograda en `marketplace` y evitar que nuevos cambios vuelvan a un bucket generico.
5. Profundizar la evaluacion sobre la base actual de responsabilidades explicitas:
   - `EvaluadorDesignado`
   - `AdjudicadorDesignado`
   - `ObservadorDeEvaluacion`
   - auditoria y gobierno mas ricos sobre empates y adjudicaciones excepcionales
6. Aumentar cobertura automatizada por invariante de dominio, no solo por flujo feliz.
7. Completar el desacople operativo del `.env` local en los flujos sensibles restantes.
8. Consolidar la estrategia de despliegue real de produccion alrededor de `gunicorn`, infraestructura externa, TLS, SMTP y configuracion segura.

## 10. Ruta sugerida por iteraciones

### Iteracion A: consolidacion documental y gobierno tecnico

Objetivo:

- convertir el modelo ya descubierto en referencia operativa estable.

Entregables:

- ADRs iniciales;
- plantilla de especificacion;
- regla de `spec-to-tests`;
- checklist de cierre tecnico por feature;
- mantenimiento sincronizado de `README.md`, `docs/domain/*` y snapshots locales de seguimiento.

### Iteracion B: formalizacion del dominio en codigo

Objetivo:

- empezar a cerrar la brecha entre modelo formal y software ejecutable.

Entregables:

- `Challenge` con `estado`, `CriterioDeEvaluacion` y `FechaLimiteDeAplicacion`;
- `Application` con cuatro componentes obligatorios de `Propuesta` y lifecycle persistido `DRAFT -> SUBMITTED`;
- `ValidadorDeRolSolicitante` como servicio de dominio nombrado;
- pruebas por invariantes criticas;
- revision de terminos y nombres en codigo y documentacion.

Observacion de estado:

- Una parte importante de esta iteracion ya fue absorbida por el codigo actual: la separacion tactica interna de `marketplace` entre challenge y application ya existe en servicios, reglas, forms, views y pruebas.

### Iteracion C: cierre de Application y apertura de Evaluation

Objetivo:

- completar el ciclo central de propuesta, evaluacion y adjudicacion.

Entregables:

- `Borrador` persistido para `Propuesta`, ya implementado;
- separacion entre `AdjudicadorDesignado` y `ObservadorDeEvaluacion`;
- ampliar los eventos de dominio explicitos y sus consumidores mas alla de inicio/adjudicacion;
- refactor de nombres tecnicos `Challenge` y `Application` cuando haya ventana segura.

Observacion de estado:

- Parte importante de esta iteracion ya fue absorbida por el codigo actual: `DecisionDeAdjudicacion` con comentario obligatorio, scoring por promedio de criterio, ranking comparativo con empates visibles, snapshot enriquecido de adjudicacion y consumidores adicionales de eventos ya existen.
- El faltante funcional real que queda en pie aqui ya no es la formalizacion de roles, la evaluacion ciega ni la politica de scoring, sino mejor auditoria, mayor gobierno de decisiones y mayor madurez operativa.

### Iteracion D: institucionalizacion y extensiones de plataforma

Objetivo:

- volver repetible la mejora arquitectonica, semantica y metodologica.

Entregables:

- `Notifications` como contexto operativo;
- decision explicita sobre `Discovery`;
- learning loop por iteracion;
- architecture review checklist;
- registro de decisiones y lecciones aprendidas;
- evaluacion de si `Administracion de plataforma` merece bounded context propio.

## 11. Conclusion

VIMER ya no esta en una fase puramente exploratoria. El repositorio muestra un MVP funcional, con arquitectura razonable, validaciones importantes, pruebas automatizadas utiles y una evolucion incremental guiada por correcciones concretas. La diferencia relevante despues de esta sesion es que el proyecto ya no depende de intuiciones dispersas para hablar de DDD y ontologias: existe un modelo de dominio formalizado, con lenguaje ubicuo gobernado, bounded contexts definidos, agregados identificados, invariantes trazables y una ontologia base utilizable.

La conclusion correcta ya no es "falta descubrir el dominio", sino "falta implementar con disciplina el dominio ya descubierto". Bajo ese criterio, VIMER queda bastante mas cerca de un compliance alto en DDD y ontologias a nivel conceptual, aunque todavia no a nivel de codigo. El siguiente salto de calidad depende de traducir este modelo al software ejecutable, a las pruebas y a la rutina de evolucion del proyecto.
