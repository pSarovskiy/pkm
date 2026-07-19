from django.core.management.base import BaseCommand
from wagtail.models import Page


class Command(BaseCommand):
    help = (
        "Runs the NLP pipeline (spaCy entities, TextBlob sentiment, "
        "sentence-transformers embedding) for every live page. "
        "Useful for the initial backfill or after changing the "
        "embedding model."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--async",
            action="store_true",
            dest="use_async",
            help="Queue each page as a Celery task instead of processing inline.",
        )

    def handle(self, *args, **options):
        pages = Page.objects.live().specific()
        total = pages.count()
        self.stdout.write(f"Найдено {total} опубликованных страниц.")

        if options["use_async"]:
            from .. import tasks

            for page in pages:
                tasks.process_page_nlp.delay(page.pk)
            self.stdout.write(self.style.SUCCESS(f"Поставлено в очередь Celery: {total} страниц."))
            return

        from ..services import run_pipeline

        for i, page in enumerate(pages, start=1):
            analysis = run_pipeline(page)
            status = self.style.ERROR("ERROR") if analysis.error else self.style.SUCCESS("OK")
            self.stdout.write(f"[{i}/{total}] {page} -> {status}")

        self.stdout.write(self.style.SUCCESS("Готово."))
