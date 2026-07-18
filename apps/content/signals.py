from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Post


@receiver(post_save, sender=Post)
def queue_nlp_processing(sender, instance: Post, created, **kwargs):
    """
    При публикации (или обновлении опубликованного) поста ставим NLP-анализ
    в очередь celery, а не выполняем синхронно в веб-процессе.
    """
    if instance.status != Post.Status.PUBLISHED:
        return

    # Локальный импорт, чтобы избежать циклических зависимостей apps.content <-> apps.nlp
    from apps.nlp.models import PostAnalysis
    from apps.nlp.tasks import process_post_nlp

    PostAnalysis.objects.update_or_create(post=instance, defaults={"is_stale": True})
    process_post_nlp.delay(instance.pk)
