from django.apps import AppConfig


class NlpConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "nlp"
    verbose_name = "NLP-обработка контента"

    def ready(self):
        # Registers the page_published/page_unpublished handlers that queue
        # the Celery task in tasks.py.
        from . import signals  # noqa: F401
