# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Builder stage: compiles Python packages (incl. spaCy/sentence-transformers
# native extensions) into a virtualenv that gets copied into the runtime
# image, keeping build tools out of the final image.
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

RUN apt-get update --yes --quiet && apt-get install --yes --quiet --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libwebp-dev \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /requirements.txt

# Download the NLP models at build time so containers start instantly and
# work fully offline at runtime (no first-request download surprise).
# NLP_SPACY_MODEL can be overridden, e.g. --build-arg NLP_SPACY_MODEL=ru_core_news_sm
ARG NLP_SPACY_MODEL=ru_core_news_sm
ARG NLP_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
COPY ru_core_news_sm-3.7.0-py3-none-any.whl /tmp/
RUN pip install --no-cache-dir /tmp/ru_core_news_sm-3.7.0-py3-none-any.whl
# RUN python -m spacy download ${NLP_SPACY_MODEL}
RUN python -c "from textblob import download_corpora" 2>/dev/null; python -m textblob.download_corpora || true
RUN python - <<PYEOF
from sentence_transformers import SentenceTransformer
SentenceTransformer("${NLP_EMBEDDING_MODEL}")
PYEOF

# ---------------------------------------------------------------------------
# Runtime stage
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

RUN apt-get update --yes --quiet && apt-get install --yes --quiet --no-install-recommends \
    libpq5 \
    libjpeg62-turbo \
    libwebp7 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home wagtail

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=myproject.settings.production

COPY --from=builder /opt/venv /opt/venv
# Pre-downloaded models (spaCy data lives inside the venv's site-packages;
# sentence-transformers/HuggingFace cache lives in the builder's HOME).
COPY --from=builder /root/.cache /home/wagtail/.cache

WORKDIR /app
COPY --chown=wagtail:wagtail . .
COPY --chown=wagtail:wagtail docker/entrypoint.prod.sh /entrypoint.prod.sh
RUN chmod +x /entrypoint.prod.sh \
    && chown -R wagtail:wagtail /app /home/wagtail/.cache

USER wagtail
EXPOSE 8000

ENTRYPOINT ["/entrypoint.prod.sh"]
CMD ["gunicorn", "myproject.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
