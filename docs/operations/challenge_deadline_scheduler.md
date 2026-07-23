# Cierre automático de convocatorias

VIMER dispone del comando idempotente:

```bash
python manage.py close_expired_challenges
```

El comando bloquea cada desafío, vuelve a comprobar estado y fecha, cambia
únicamente `PUBLISHED` vencidos a `CLOSED`, registra un evento automático sin
suplantar un actor humano y emite las notificaciones correspondientes. Puede
repetirse sin duplicar la transición.

`close_expired_challenges` está integrado en el servicio Compose `scheduler`
junto con `expire_join_requests`. Su intervalo se define mediante
`CHALLENGE_CLOSURE_INTERVAL_SECONDS` —900 segundos por defecto— y los reintentos
mediante `SCHEDULER_RETRY_DELAY_SECONDS`.

El scheduler ejecuta primero `manage.py migrate --check`. Su heartbeat conserva
por separado el último éxito de ambos jobs y el healthcheck falla si cualquiera
queda obsoleto. Debe desplegarse una sola réplica del scheduler.
