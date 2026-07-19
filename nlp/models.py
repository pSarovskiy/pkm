from django.conf import settings
from django.db import models
from pgvector.django import HnswIndex, VectorField


class PageAnalysis(models.Model):
    """
    Result of the NLP pipeline for a single Wagtail page:
      - named entities extracted with spaCy
      - sentiment (polarity/subjectivity) computed with TextBlob
      - a sentence-transformers embedding stored as a pgvector column,
        used for semantic similarity search ("find pages like this one").

    One row per page, refreshed every time the page is published
    (see nlp/signals.py -> nlp/tasks.py).
    """

    page = models.OneToOneField(
        "wagtailcore.Page",
        on_delete=models.CASCADE,
        related_name="nlp_analysis",
    )

    # Plain text that was actually analysed (extracted from the page's
    # rich text / stream fields), kept for debugging & re-processing.
    source_text = models.TextField(blank=True)

    # --- spaCy named-entity recognition -------------------------------
    # List of {"text": ..., "label": ..., "start": ..., "end": ...}
    entities = models.JSONField(default=list, blank=True)

    # --- TextBlob sentiment --------------------------------------------
    sentiment_polarity = models.FloatField(null=True, blank=True)
    sentiment_subjectivity = models.FloatField(null=True, blank=True)

    # --- sentence-transformers embedding --------------------------------
    # Dimensions must match settings.NLP_EMBEDDING_DIMENSIONS
    # (384 for the default "all-MiniLM-L6-v2" model).
    embedding = VectorField(dimensions=384, null=True, blank=True)

    model_name = models.CharField(max_length=200, blank=True)
    processed_at = models.DateTimeField(auto_now=True)
    error = models.TextField(blank=True)

    class Meta:
        verbose_name = "Результат NLP-анализа страницы"
        verbose_name_plural = "Результаты NLP-анализа страниц"
        indexes = [
            # Approximate nearest-neighbour index for cosine similarity
            # search over the embedding column. HNSW is the pgvector-
            # recommended index type for read-heavy similarity search.
            HnswIndex(
                name="pageanalysis_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self):
        return f"NLP-анализ: {self.page}"
