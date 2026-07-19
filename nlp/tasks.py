import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=10,
    retry_backoff_max=300,
    max_retries=3,
)
def process_page_nlp(self, page_id: int):
    """
    Runs entity extraction (spaCy), sentiment analysis (TextBlob) and
    embedding computation (sentence-transformers) for a single page, and
    stores the result in nlp.models.PageAnalysis.

    Queued from nlp/signals.py whenever a page is published, so that the
    (potentially slow, model-inference-heavy) work happens in a Celery
    worker instead of blocking the Wagtail admin request.
    """
    from wagtail.models import Page

    from .services import run_pipeline

    try:
        page = Page.objects.get(pk=page_id).specific
    except Page.DoesNotExist:
        logger.warning("process_page_nlp: page %s no longer exists, skipping", page_id)
        return

    analysis = run_pipeline(page)
    if analysis.error:
        logger.warning("NLP pipeline finished with an error for page %s: %s", page_id, analysis.error)
    else:
        logger.info("NLP pipeline finished for page %s", page_id)
