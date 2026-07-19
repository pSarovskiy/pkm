from django.conf import settings
from wagtail.signals import page_published


def queue_nlp_processing(sender, instance, **kwargs):
    from .tasks import process_page_nlp

    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        # In dev this runs synchronously in-process; in production it is
        # always dispatched to the Celery worker via Redis.
        process_page_nlp(instance.pk)
    else:
        process_page_nlp.delay(instance.pk)


page_published.connect(queue_nlp_processing)
