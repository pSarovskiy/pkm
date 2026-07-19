"""
NLP pipeline used to enrich Wagtail pages:

  1. extract_page_text(page)  -> plain text pulled out of the page's
     indexed fields (title + every field registered as index.SearchField,
     which works for any page type, including RichText and StreamField).
  2. extract_entities(text)   -> named entities via spaCy.
  3. analyze_sentiment(text)  -> polarity/subjectivity via TextBlob.
  4. compute_embedding(text)  -> a vector via sentence-transformers.
  5. run_pipeline(page)       -> runs all of the above and stores the
     result in nlp.models.PageAnalysis (called from nlp/tasks.py).

All heavyweight ML libraries (spaCy, TextBlob, sentence-transformers) are
imported lazily, inside functions, and the loaded models are cached at
module level (`_spacy_nlp`, `_st_model`). This keeps `manage.py` commands
and Django startup fast, and means the models are only loaded once per
worker process (in the Celery worker), not once per task.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

_spacy_nlp = None
_st_model = None


# ---------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------

def extract_page_text(page) -> str:
    """
    Builds a plain-text representation of a Wagtail page by walking its
    `search_fields` (the same mechanism Wagtail's own search index uses),
    so this works for any page type without page-specific code.
    """
    from wagtail.search import index

    specific = page.specific  # resolve to the actual page subclass
    chunks: list[str] = []

    for field in getattr(specific, "search_fields", []):
        if not isinstance(field, index.SearchField):
            continue
        try:
            value = field.get_value(specific)
        except Exception:  # pragma: no cover - defensive, keep pipeline alive
            logger.exception("Failed to read field %s on page %s", field.field_name, page.pk)
            continue

        if value is None:
            continue
        if callable(value):
            value = value()

        text = strip_tags(str(value)).strip()
        if text:
            chunks.append(text)

    return "\n\n".join(chunks)


# ---------------------------------------------------------------------
# spaCy named-entity recognition
# ---------------------------------------------------------------------

def _get_spacy_model():
    global _spacy_nlp
    if _spacy_nlp is None:
        import spacy

        model_name = settings.NLP_SPACY_MODEL
        try:
            _spacy_nlp = spacy.load(model_name)
        except OSError:
            # Model not downloaded (should not happen in the Docker image,
            # see Dockerfile's `python -m spacy download`, but keeps
            # local/dev environments from hard-failing).
            logger.warning(
                "spaCy model '%s' is not installed; run "
                "'python -m spacy download %s'. Falling back to a blank "
                "pipeline (no entity recognition).",
                model_name,
                model_name,
            )
            _spacy_nlp = spacy.blank("en")
    return _spacy_nlp


def extract_entities(text: str) -> list[dict]:
    if not text:
        return []
    nlp = _get_spacy_model()
    doc = nlp(text)
    return [
        {
            "text": ent.text,
            "label": ent.label_,
            "start": ent.start_char,
            "end": ent.end_char,
        }
        for ent in doc.ents
    ]


# ---------------------------------------------------------------------
# TextBlob sentiment
# ---------------------------------------------------------------------

def analyze_sentiment(text: str) -> tuple[float | None, float | None]:
    if not text:
        return None, None
    from textblob import TextBlob

    blob = TextBlob(text)
    return blob.sentiment.polarity, blob.sentiment.subjectivity


# ---------------------------------------------------------------------
# sentence-transformers embedding
# ---------------------------------------------------------------------

def _get_embedding_model():
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer

        _st_model = SentenceTransformer(settings.NLP_EMBEDDING_MODEL)
    return _st_model


def compute_embedding(text: str) -> list[float] | None:
    if not text:
        return None
    model = _get_embedding_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


# ---------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------

def run_pipeline(page) -> "PageAnalysis":  # noqa: F821 - forward ref, avoids import cycle
    from .models import PageAnalysis

    text = extract_page_text(page)
    analysis, _created = PageAnalysis.objects.get_or_create(page=page)
    analysis.source_text = text
    analysis.error = ""

    try:
        analysis.entities = extract_entities(text)
        polarity, subjectivity = analyze_sentiment(text)
        analysis.sentiment_polarity = polarity
        analysis.sentiment_subjectivity = subjectivity
        analysis.embedding = compute_embedding(text)
        analysis.model_name = settings.NLP_EMBEDDING_MODEL
    except Exception as exc:  # keep the failure visible without crashing the task
        logger.exception("NLP pipeline failed for page %s", page.pk)
        analysis.error = str(exc)

    analysis.save()
    return analysis


def find_similar_pages(page, limit: int = 5):
    """
    Returns the `limit` pages whose embedding is closest (cosine distance)
    to the given page's embedding. Requires that both pages have already
    been processed by run_pipeline().
    """
    from pgvector.django import CosineDistance

    from .models import PageAnalysis

    try:
        source = page.nlp_analysis
    except PageAnalysis.DoesNotExist:
        return PageAnalysis.objects.none()

    if source.embedding is None:
        return PageAnalysis.objects.none()

    return (
        PageAnalysis.objects.exclude(pk=source.pk)
        .filter(embedding__isnull=False)
        .annotate(distance=CosineDistance("embedding", source.embedding))
        .order_by("distance")[:limit]
    )
