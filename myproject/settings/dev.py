from .base import *  # noqa: F401,F403

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DJANGO_DEBUG", default=True)

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["*"])

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Convenient in dev: run Celery tasks synchronously (in-process) unless
# a worker container is explicitly used.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)

try:
    from .local import *  # noqa: F401,F403
except ImportError:
    pass
