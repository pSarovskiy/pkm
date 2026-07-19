import os

from celery import Celery

# Same default as manage.py/wsgi.py; overridden in docker-compose via the
# DJANGO_SETTINGS_MODULE environment variable (dev vs production).
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings.dev")

app = Celery("myproject")

# Read CELERY_* settings from Django settings (see myproject/settings/base.py).
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py in every installed app (e.g. nlp/tasks.py).
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
