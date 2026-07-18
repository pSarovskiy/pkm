import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_post_nlp(self, post_id: int):
    """
    Асинхронно прогоняет пост через NLP-пайплайн:
      1. spaCy       -> именованные сущности
      2. TextBlob    -> тональность
      3. sentence-transformers -> эмбеддинг, сохраняется в pgvector
    Запускается сигналом post_save при публикации поста (см. apps/content/signals.py).
    """
    from apps.content.models import Post
    from apps.nlp.models import PostAnalysis, PostEntity
    from apps.nlp.services import NLPPipeline

    try:
        post = Post.objects.get(pk=post_id)
    except Post.DoesNotExist:
        logger.warning("process_post_nlp: пост id=%s не найден, пропускаем", post_id)
        return

    pipeline = NLPPipeline()
    result = pipeline.process(post.title, post.content)

    # Пересобираем сущности
    PostEntity.objects.filter(post=post).delete()
    PostEntity.objects.bulk_create(
        [
            PostEntity(
                post=post,
                text=e.text,
                label=e.label,
                start_char=e.start_char,
                end_char=e.end_char,
            )
            for e in result["entities"]
        ]
    )

    analysis, _ = PostAnalysis.objects.get_or_create(post=post)
    analysis.sentiment_polarity = result["sentiment"].polarity
    analysis.sentiment_subjectivity = result["sentiment"].subjectivity
    analysis.embedding = result["embedding"]
    analysis.embedding_model = result["embedding_model"]
    analysis.processed_at = timezone.now()
    analysis.is_stale = False
    analysis.save()

    logger.info("NLP-анализ поста id=%s завершён (сущностей: %s)", post_id, len(result["entities"]))
    return {"post_id": post_id, "entities": len(result["entities"])}


@shared_task
def reprocess_stale_posts():
    """Периодическая задача (django-celery-beat): пересчитать всё, что помечено как устаревшее."""
    from apps.nlp.models import PostAnalysis

    stale_ids = list(
        PostAnalysis.objects.filter(is_stale=True).values_list("post_id", flat=True)
    )
    for post_id in stale_ids:
        process_post_nlp.delay(post_id)
    return {"queued": len(stale_ids)}
