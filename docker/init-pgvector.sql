-- Runs automatically on first container start (mounted into
-- /docker-entrypoint-initdb.d/ of the pgvector/pgvector image, see
-- docker-compose.yml). Belt-and-braces alongside the Django migration
-- nlp/migrations/0001_enable_pgvector.py, which also enables this
-- extension -- having it here means it's available immediately even
-- before migrations run.
CREATE EXTENSION IF NOT EXISTS vector;
