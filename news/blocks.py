from wagtail.blocks import (
    CharBlock,
    RichTextBlock,
    StreamBlock,
    StructBlock,
    ListBlock,
    ChoiceBlock,
    BooleanBlock,
)
from wagtail.images.blocks import ImageChooserBlock
from wagtail.embeds.blocks import EmbedBlock


class ImageWithCaptionBlock(StructBlock):
    image = ImageChooserBlock()
    caption = CharBlock(required=False, label="Подпись")

    class Meta:
        icon = "image"
        template = "news/blocks/image_with_caption.html"
        label = "Изображение с подписью"


class QuoteBlock(StructBlock):
    text = RichTextBlock(label="Текст цитаты", features=["bold", "italic", "link"])
    author = CharBlock(required=False, label="Автор")

    class Meta:
        icon = "openquote"
        template = "news/blocks/quote.html"
        label = "Цитата"


class ChecklistItemBlock(StructBlock):
    label = CharBlock(label="Текст пункта")
    checked = BooleanBlock(required=False, label="Отмечено по умолчанию")


class ChecklistBlock(StructBlock):
    items = ListBlock(ChecklistItemBlock(), label="Пункты")

    class Meta:
        icon = "list-ul"
        template = "news/blocks/checklist.html"
        label = "Чеклист"


class SimpleListBlock(StructBlock):
    items = ListBlock(CharBlock(label="Элемент"), label="Элементы списка")
    ordered = BooleanBlock(required=False, default=False, label="Нумерованный")

    class Meta:
        icon = "list-ul"
        template = "news/blocks/simple_list.html"
        label = "Список"


class ProsConsBlock(StructBlock):
    pros = ListBlock(CharBlock(label="Плюс"), label="Плюсы")
    cons = ListBlock(CharBlock(label="Минус"), label="Минусы")

    class Meta:
        icon = "table"
        template = "news/blocks/pros_cons.html"
        label = "За и против"


class StatBlock(StructBlock):
    value = CharBlock(label="Значение", help_text="Например: 150, 2.5 млн, +35%")
    label = CharBlock(label="Подпись")
    description = RichTextBlock(required=False, label="Доп. описание", features=["bold", "italic"])

    class Meta:
        icon = "desktop"
        template = "news/blocks/stat.html"
        label = "Статистика"


class GalleryImageBlock(StructBlock):
    image = ImageChooserBlock(label="Изображение")
    caption = CharBlock(required=False, label="Подпись")


class GalleryBlock(StructBlock):
    images = ListBlock(GalleryImageBlock(), label="Изображения")

    class Meta:
        icon = "image"
        template = "news/blocks/gallery.html"
        label = "Галерея"


class FAQItemBlock(StructBlock):
    question = CharBlock(label="Вопрос")
    answer = RichTextBlock(
        label="Ответ",
        features=["bold", "italic", "link", "ul", "ol"],
    )


class FAQBlock(StructBlock):
    items = ListBlock(FAQItemBlock(), label="Вопросы и ответы")

    class Meta:
        icon = "help"
        template = "news/blocks/faq.html"
        label = "FAQ"


class CalloutBlock(StructBlock):
    type = ChoiceBlock(
        choices=[
            ("info", "Информация"),
            ("warning", "Предупреждение"),
            ("success", "Успех"),
            ("danger", "Важно"),
        ],
        default="info",
        label="Тип",
    )
    text = RichTextBlock(label="Текст", features=["bold", "italic", "link"])
    icon = CharBlock(required=False, label="Иконка (CSS-класс)", help_text="Например: fa-info-circle")

    class Meta:
        icon = "warning"
        template = "news/blocks/callout.html"
        label = "Выноска"


class HeadingBlock(StructBlock):
    level = ChoiceBlock(
        choices=[
            ('h2', 'H2'),
            ('h3', 'H3'),
            ('h4', 'H4'),
        ],
        default='h3',
        label="Уровень заголовка"
    )
    text = CharBlock(label="Текст заголовка")

    class Meta:
        icon = "title"
        template = "news/blocks/heading.html"
        label = "Заголовок"


class NewsStreamBlock(StreamBlock):
    heading = HeadingBlock()
    paragraph = RichTextBlock(
        icon="pilcrow",
        label="Текст",
        features=[
            "bold",
            "italic",
            "underline",
            "ol",
            "ul",
            "link",
            "hr",
            "blockquote",
        ],
    )
    image = ImageWithCaptionBlock()
    embed = EmbedBlock(
        icon="media",
        label="Embed (видео / карта)",
        help_text="Ссылка на YouTube, Яндекс.Карты, Google Maps и т.д.",
    )
    quote = QuoteBlock()
    checklist = ChecklistBlock()
    simple_list = SimpleListBlock()
    pros_cons = ProsConsBlock()
    stat = StatBlock()
    gallery = GalleryBlock()
    faq = FAQBlock()
    callout = CalloutBlock()