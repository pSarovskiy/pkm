#!/usr/bin/env bash
# Dev entrypoint: waits for PostgreSQL, runs migrations, then hands off
# to whatever command docker-compose.yml specifies (runserver by default).
# No collectstatic here -- Django's runserver serves static files itself
# while DEBUG=True.
#
# Invoked explicitly as `bash docker/entrypoint.dev.sh` from
# docker-compose.yml (not chmod +x) so it keeps working even if the
# executable bit gets lost when this file is edited/saved from Windows.
set -euo pipefail

echo "[entrypoint-dev] Waiting for PostgreSQL at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
python <<'PYEOF'
import os
import sys
import time

import psycopg2

host = os.environ.get("POSTGRES_HOST", "db")
port = os.environ.get("POSTGRES_PORT", "5432")
dbname = os.environ.get("POSTGRES_DB", "wagtail")
user = os.environ.get("POSTGRES_USER", "wagtail")
password = os.environ.get("POSTGRES_PASSWORD", "wagtail")

for attempt in range(1, 31):
    try:
        conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
        conn.close()
        break
    except psycopg2.OperationalError as exc:
        print(f"  attempt {attempt}/30: {exc}", file=sys.stderr)
        time.sleep(2)
else:
    print("PostgreSQL did not become available in time", file=sys.stderr)
    sys.exit(1)
PYEOF
echo "[entrypoint-dev] PostgreSQL is up."

echo "[entrypoint-dev] Running migrations..."
python manage.py migrate --noinput

echo "[entrypoint-dev] Starting: $*"
exec "$@"
