from django.apps import AppConfig


class EvaluationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.evaluation"
    verbose_name = "Evaluación"

    def ready(self):
        import apps.evaluation.domain.handlers  # noqa: F401
