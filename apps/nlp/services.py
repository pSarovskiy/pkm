"""
Сервисный слой NLP-пайплайна.

Модели (spaCy, sentence-transformers) тяжёлые, поэтому загружаются один раз
на процесс (ленивая инициализация + module-level кеш), а не при каждом вызове.
В production это должно исполняться в celery-воркере, а не в веб-процессе,
чтобы не блокировать обработку HTTP-запросов.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    text: str
    label: str
    start_char: int
    end_char: int


@dataclass
class SentimentResult:
    polarity: float
    subjectivity: float


def _clean_text(html_or_text: str) -> str:
    """Грубая очистка HTML-разметки перед прогоном через NLP-модели."""
    text = re.sub(r"<[^>]+>", " ", html_or_text or "")
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=1)
def get_spacy_model():
    import spacy

    model_name = settings.SPACY_MODEL
    try:
        return spacy.load(model_name)
    except OSError:
        logger.warning(
            "Модель spaCy '%s' не найдена локально. Убедитесь, что при сборке "
            "образа выполнена команда `python -m spacy download %s`.",
            model_name,
            model_name,
        )
        raise


@lru_cache(maxsize=1)
def get_embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.EMBEDDING_MODEL)


class EntityExtractor:
    """Извлечение именованных сущностей через spaCy (NER)."""

    def extract(self, text: str) -> list[ExtractedEntity]:
        nlp = get_spacy_model()
        doc = nlp(_clean_text(text))
        return [
            ExtractedEntity(
                text=ent.text,
                label=ent.label_,
                start_char=ent.start_char,
                end_char=ent.end_char,
            )
            for ent in doc.ents
        ]


class SentimentAnalyzer:
    """
    Анализ тональности через TextBlob.

    Примечание: TextBlob "из коробки" рассчитан на английский текст.
    Для русскоязычного контента точность будет ограниченной — при необходимости
    замените на модель на основе transformers (например, rubert-tiny-sentiment),
    сохранив тот же интерфейс `analyze(text) -> SentimentResult`.
    """

    def analyze(self, text: str) -> SentimentResult:
        from textblob import TextBlob

        blob = TextBlob(_clean_text(text))
        return SentimentResult(
            polarity=round(blob.sentiment.polarity, 4),
            subjectivity=round(blob.sentiment.subjectivity, 4),
        )


class Embedder:
    """Преобразование текста в векторное представление (sentence-transformers)."""

    def encode(self, text: str) -> list[float]:
        model = get_embedding_model()
        vector = model.encode(_clean_text(text), normalize_embeddings=True)
        return vector.tolist()

    @property
    def model_name(self) -> str:
        return settings.EMBEDDING_MODEL


class NLPPipeline:
    """Фасад, объединяющий все три этапа обработки текста."""

    def __init__(self):
        self.entities = EntityExtractor()
        self.sentiment = SentimentAnalyzer()
        self.embedder = Embedder()

    def process(self, title: str, content: str) -> dict:
        full_text = f"{title}\n\n{content}"
        return {
            "entities": self.entities.extract(full_text),
            "sentiment": self.sentiment.analyze(full_text),
            "embedding": self.embedder.encode(full_text),
            "embedding_model": self.embedder.model_name,
        }
