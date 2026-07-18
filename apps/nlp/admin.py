from django.contrib import admin

from .models import PostAnalysis, PostEntity


class PostEntityInline(admin.TabularInline):
    model = PostEntity
    extra = 0
    readonly_fields = ("text", "label", "start_char", "end_char")
    can_delete = False


@admin.register(PostAnalysis)
class PostAnalysisAdmin(admin.ModelAdmin):
    list_display = ("post", "sentiment_label", "sentiment_polarity", "sentiment_subjectivity", "processed_at", "is_stale")
    list_filter = ("is_stale", "embedding_model")
    readonly_fields = ("processed_at",)
    search_fields = ("post__title",)


@admin.register(PostEntity)
class PostEntityAdmin(admin.ModelAdmin):
    list_display = ("text", "label", "post")
    list_filter = ("label",)
    search_fields = ("text", "post__title")
