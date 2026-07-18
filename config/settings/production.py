from .base import *  # noqa

DEBUG = False

# ---------------------------------------------------------------------------
# HTTPS / secure cookies
# ---------------------------------------------------------------------------
# ВАЖНО: SESSION_COOKIE_SECURE / CSRF_COOKIE_SECURE говорят браузеру
# "отправляй эту cookie только по HTTPS". Если сайт реально отдаётся по HTTP
# (например, nginx ещё без сертификата), браузер тихо перестаёт слать cookie
# обратно — сессия каждый раз выглядит "новой", и админка просит логиниться
# заново на каждое действие. Поэтому эти флаги включаются только когда
# USE_HTTPS=True в .env (то есть когда перед Django реально стоит TLS-терминатор,
# который прокидывает заголовок X-Forwarded-Proto: https — см. nginx/nginx.conf).
USE_HTTPS = env.bool("USE_HTTPS", default=False)

SECURE_SSL_REDIRECT = USE_HTTPS
SESSION_COOKIE_SECURE = USE_HTTPS
CSRF_COOKIE_SECURE = USE_HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if USE_HTTPS else None

if USE_HTTPS:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Django 4+ требует явно перечислять источники для CSRF-проверки

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "apps": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
