from django.contrib import admin

from .models import PageAnalysis


@admin.register(PageAnalysis)
class PageAnalysisAdmin(admin.ModelAdmin):
    list_display = ("page", "sentiment_polarity", "sentiment_subjectivity", "processed_at", "model_name")
    readonly_fields = (
        "page",
        "source_text",
        "entities",
        "sentiment_polarity",
        "sentiment_subjectivity",
        "embedding",
        "model_name",
        "processed_at",
        "error",
    )
    search_fields = ("page__title", "source_text")
