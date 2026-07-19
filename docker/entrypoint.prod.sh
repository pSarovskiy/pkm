#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] Waiting for PostgreSQL at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
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
echo "[entrypoint] PostgreSQL is up."

echo "[entrypoint] Running migrations..."
python manage.py migrate --noinput

echo "[entrypoint] Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "[entrypoint] Starting: $*"
exec "$@"
