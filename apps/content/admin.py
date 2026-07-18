from django.contrib import admin

from apps.nlp.admin import PostEntityInline

from .models import Category, Comment, Media, Page, Post, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ("file", "uploaded_by", "uploaded_at")
    readonly_fields = ("uploaded_at",)


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ("author", "author_name", "content", "created_at")
    fields = ("author", "author_name", "content", "is_approved", "created_at")


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "status", "published_at", "views_count")
    list_filter = ("status", "category", "tags")
    search_fields = ("title", "content")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ["category", "tags"]
    inlines = [PostEntityInline, CommentInline]
    actions = ["make_published"]

    @admin.action(description="Опубликовать выбранные записи")
    def make_published(self, request, queryset):
        for post in queryset:
            post.publish()  # триггерит сигнал -> постановку NLP-задачи в очередь


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "status", "menu_order")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("display_name", "post", "is_approved", "created_at")
    list_filter = ("is_approved",)
    actions = ["approve_comments"]

    @admin.action(description="Одобрить выбранные комментарии")
    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)
