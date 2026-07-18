from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ["*"]

CACHES["default"]["BACKEND"] = "django.core.cache.backends.locmem.LocMemCache"  # noqa: F405
del CACHES["default"]["LOCATION"]  # noqa: F405

# В деве можно выполнять celery-задачи синхронно, без брокера
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)  # noqa: F405
CELERY_TASK_EAGER_PROPAGATES = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
