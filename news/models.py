from django.conf import settings
from django.db import models

from modelcluster.contrib.taggit import ClusterTaggableManager
from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from taggit.models import TaggedItemBase

from wagtail.admin.forms import WagtailAdminPageForm
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.blocks import CharBlock, RichTextBlock, StreamBlock, StructBlock
from wagtail.embeds.blocks import EmbedBlock
from wagtail.fields import RichTextField, StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtail.images.models import Image
from wagtail.models import Orderable, Page
from wagtail.search import index
from wagtail.snippets.models import register_snippet


# --- Локация (город/район) — таксономия под тематику недвижимости --------

@register_snippet
class Location(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название")
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children",
        verbose_name="Родительская локация (например, город для района)",
    )

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("parent"),
    ]

    class Meta:
        verbose_name = "Локация"
        verbose_name_plural = "Локации"
        ordering = ["name"]

    def __str__(self):
        return self.name


# --- Автор (карточка для публичного отображения, опционально связана
#     с реальным логином CMS — для авто-подстановки при создании поста) ---

@register_snippet
class Author(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="author_profile",
        verbose_name="Связанный аккаунт CMS",
        help_text=(
            "Если заполнено — этот автор будет автоматически подставляться "
            "в новых постах, которые создаёт этот пользователь."
        ),
    )
    name = models.CharField(max_length=150, verbose_name="Имя")
    position = models.CharField(max_length=200, blank=True, verbose_name="Должность")
    photo = models.ForeignKey(
        Image, null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )
    bio = models.TextField(blank=True, verbose_name="Краткая биография")

    panels = [
        FieldPanel("user"),
        FieldPanel("name"),
        FieldPanel("position"),
        FieldPanel("photo"),
        FieldPanel("bio"),
    ]

    class Meta:
        verbose_name = "Автор"
        verbose_name_plural = "Авторы"
        ordering = ["name"]

    def __str__(self):
        return self.name


# --- Категории (таксономия, как Category в WP) ----------------------------

@register_snippet
class NewsCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("parent"),
    ]

    class Meta:
        verbose_name = "Категория новости"
        verbose_name_plural = "Категории новостей"
        ordering = ["name"]

    def __str__(self):
        return self.name


# --- Теги (django-taggit, как Tag в WP) ------------------------------------

class NewsPageTag(TaggedItemBase):
    content_object = ParentalKey(
        "news.NewsPage", related_name="tagged_items", on_delete=models.CASCADE
    )


# --- StreamField-блоки для тела статьи -------------------------------------

class ImageWithCaptionBlock(StructBlock):
    image = ImageChooserBlock()
    caption = CharBlock(required=False, label="Подпись")

    class Meta:
        icon = "image"
        template = "news/blocks/image_with_caption.html"
        label = "Изображение с подписью"


class NewsStreamBlock(StreamBlock):
    heading = CharBlock(icon="title", label="Подзаголовок")
    paragraph = RichTextBlock(icon="pilcrow", label="Текст")
    image = ImageWithCaptionBlock()
    embed = EmbedBlock(
        icon="media",
        label="Embed (видео / карта)",
        help_text="Ссылка на YouTube, Яндекс.Карты, Google Maps и т.д.",
    )


# --- Индексная страница (родитель, задаёт префикс /n/) --------------------

class NewsIndexPage(RoutablePageMixin, Page):
    """
    ВАЖНО: у этой страницы в дереве Wagtail должен быть slug "n" -- тогда
    все дочерние NewsPage будут иметь адрес site.ru/n/<slug поста>/.

    Красивые URL фильтров вместо query-параметров:
      /n/с/<slug категории>/
      /n/t/<slug тега>/
      /n/l/<slug локации>/
    реализованы через RoutablePageMixin -- обычные пути страниц (посты)
    Wagtail резолвит по дереву раньше, чем доходит до этих route,
    поэтому конфликтов со слагами постов не возникает.
    """
    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [FieldPanel("intro")]
    subpage_types = ["news.NewsPage"]

    def _build_news_queryset(self, category_slug=None, tag_slug=None, location_slug=None):
        news = NewsPage.objects.live().descendant_of(self).order_by("-first_published_at")
        if category_slug:
            news = news.filter(categories__slug=category_slug)
        if tag_slug:
            news = news.filter(tags__slug=tag_slug)
        if location_slug:
            news = news.filter(location__slug=location_slug)
        return news

    def get_context(self, request, *args, **kwargs):
        from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

        category_slug = kwargs.get("category_slug")
        tag_slug = kwargs.get("tag_slug")
        location_slug = kwargs.get("location_slug")

        context = super().get_context(request, *args, **kwargs)
        news = self._build_news_queryset(category_slug, tag_slug, location_slug)

        paginator = Paginator(news, 12)
        page_number = request.GET.get("page", 1)
        try:
            news = paginator.page(page_number)
        except PageNotAnInteger:
            news = paginator.page(1)
        except EmptyPage:
            news = paginator.page(paginator.num_pages)

        context["news_pages"] = news
        context["categories"] = NewsCategory.objects.all()
        context["locations"] = Location.objects.all()
        context["current_category_slug"] = category_slug
        context["current_tag_slug"] = tag_slug
        context["current_location_slug"] = location_slug
        return context

    @route(r"^$")
    def index_route(self, request):
        return self.serve(request)

    @route(r"^с/(?P<category_slug>[-\w]+)/$")
    def category_route(self, request, category_slug):
        return self.render(request, context_overrides={"category_slug": category_slug})

    @route(r"^t/(?P<tag_slug>[-\w]+)/$")
    def tag_route(self, request, tag_slug):
        return self.render(request, context_overrides={"tag_slug": tag_slug})

    @route(r"^l/(?P<location_slug>[-\w]+)/$")
    def location_route(self, request, location_slug):
        return self.render(request, context_overrides={"location_slug": location_slug})


# --- Форма редактирования поста: авто-подстановка и ограничение доступа
#     к полю "Автор" ------------------------------------------------------

class NewsPageForm(WagtailAdminPageForm):
    AUTHOR_CHANGE_GROUP = "Moderators"  # стандартная группа Wagtail

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        user = self.for_user

        # Авто-подстановка автора при СОЗДАНИИ нового поста, если у
        # текущего пользователя есть привязанная карточка Author и поле
        # ещё не заполнено вручную.
        if not self.instance.pk and not self.initial.get("author"):
            matched_author = Author.objects.filter(user=user).first()
            if matched_author:
                self.fields["author"].initial = matched_author.pk

        # Менять автора руками может только модератор или суперпользователь
        # (админ). Остальным поле показывается, но недоступно для правки.
        can_change_author = bool(
            user
            and (user.is_superuser or user.groups.filter(name=self.AUTHOR_CHANGE_GROUP).exists())
        )
        if not can_change_author:
            self.fields["author"].disabled = True
            self.fields["author"].help_text = (
                "Автор подставляется автоматически. Изменить может только "
                "модератор или администратор."
            )


# --- Пост -------------------------------------------------------------

class NewsPage(Page):
    base_form_class = NewsPageForm

    date = models.DateField("Дата публикации")
    intro = models.CharField(max_length=250, blank=True)
    body = StreamField(NewsStreamBlock(), blank=True, use_json_field=True)

    main_image = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Основное изображение",
    )

    location = models.ForeignKey(
        Location, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pages", verbose_name="Город/район",
    )
    author = models.ForeignKey(
        Author, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pages", verbose_name="Автор",
    )
    source_name = models.CharField(max_length=200, blank=True, verbose_name="Источник (название)")
    source_url = models.URLField(blank=True, verbose_name="Источник (ссылка)")

    views_count = models.PositiveIntegerField(default=0, editable=False)

    categories = ParentalManyToManyField("news.NewsCategory", blank=True, related_name="pages")
    tags = ClusterTaggableManager(through="news.NewsPageTag", blank=True)

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("body"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("date"),
        FieldPanel("author"),
        FieldPanel("location"),
        FieldPanel("intro"),
        FieldPanel("main_image"),
        FieldPanel("body"),
        FieldPanel("categories"),
        FieldPanel("tags"),
        InlinePanel("gallery_images", label="Галерея изображений"),
        FieldPanel("source_name"),
        FieldPanel("source_url"),
    ]

    parent_page_types = ["news.NewsIndexPage"]
    subpage_types = []

    def get_context(self, request):
        context = super().get_context(request)

        # Простой счётчик просмотров (без защиты от накрутки —
        # для честной статистики позже можно завязать на сессию/IP)
        NewsPage.objects.filter(pk=self.pk).update(views_count=models.F("views_count") + 1)

        context["related_news"] = (
            NewsPage.objects.live()
            .exclude(pk=self.pk)
            .filter(categories__in=self.categories.all())
            .distinct()
            .order_by("-first_published_at")[:4]
        )
        return context

    @property
    def reading_time_minutes(self) -> int:
        """Грубая оценка времени чтения по количеству слов в StreamField."""
        word_count = 0
        for block in self.body:
            if block.block_type == "paragraph":
                from django.utils.html import strip_tags
                word_count += len(strip_tags(str(block.value)).split())
            elif block.block_type == "heading":
                word_count += len(str(block.value).split())
        return max(1, round(word_count / 200))  # ~200 слов/мин


# --- Галерея изображений (Orderable = сортируемый инлайн-блок) ------------

class NewsPageGalleryImage(Orderable):
    page = ParentalKey(NewsPage, on_delete=models.CASCADE, related_name="gallery_images")
    image = models.ForeignKey(Image, on_delete=models.CASCADE, related_name="+")
    caption = models.CharField(blank=True, max_length=250)

    panels = [
        FieldPanel("image"),
        FieldPanel("caption"),
    ]