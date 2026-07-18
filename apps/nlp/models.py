from django.conf import settings
from django.db import models
from pgvector.django import HnswIndex, VectorField

from apps.content.models import Post


class PostEntity(models.Model):
    """Именованные сущности, извлечённые из текста поста с помощью spaCy."""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="entities")
    text = models.CharField(max_length=500)
    label = models.CharField(max_length=50)  # PER, ORG, LOC, GPE, DATE ...
    start_char = models.IntegerField()
    end_char = models.IntegerField()

    class Meta:
        verbose_name = "Именованная сущность"
        verbose_name_plural = "Именованные сущности"
        indexes = [models.Index(fields=["post", "label"])]

    def __str__(self):
        return f"{self.text} ({self.label})"


class PostAnalysis(models.Model):
    """
    Результат NLP-анализа поста:
    - тональность (TextBlob: полярность и субъективность)
    - векторное представление текста (sentence-transformers), хранится в pgvector
    """

    post = models.OneToOneField(Post, on_delete=models.CASCADE, related_name="analysis")

    sentiment_polarity = models.FloatField(null=True, blank=True)      # -1.0 .. 1.0
    sentiment_subjectivity = models.FloatField(null=True, blank=True)  #  0.0 .. 1.0

    # Размерность должна совпадать с settings.EMBEDDING_DIM
    # (по умолчанию 384 для paraphrase-multilingual-MiniLM-L12-v2)
    embedding = VectorField(dimensions=settings.EMBEDDING_DIM, null=True, blank=True)

    embedding_model = models.CharField(max_length=200, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    is_stale = models.BooleanField(default=True)  # True — требует пересчёта

    class Meta:
        verbose_name = "NLP-анализ записи"
        verbose_name_plural = "NLP-анализ записей"
        indexes = [
            HnswIndex(
                name="post_embedding_hnsw_idx",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    @property
    def sentiment_label(self):
        if self.sentiment_polarity is None:
            return "не проанализировано"
        if self.sentiment_polarity > 0.15:
            return "позитивная"
        if self.sentiment_polarity < -0.15:
            return "негативная"
        return "нейтральная"

    def __str__(self):
        return f"Анализ: {self.post.title}"
