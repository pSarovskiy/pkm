from django.db import models

from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.search import index


class HomePage(Page):
    intro = RichTextField(blank=True, help_text="Вступительный текст главной страницы")

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    # Registering "intro" as a SearchField makes it part of Wagtail's own
    # search index, and is also what the NLP pipeline (nlp/services.py)
    # walks to build the plain text it feeds to spaCy / TextBlob /
    # sentence-transformers.
    search_fields = Page.search_fields + [
        index.SearchField("intro"),
    ]
