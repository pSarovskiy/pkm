from django.contrib.syndication.views import Feed

from .models import NewsPage
from django.utils.html import strip_tags


class NewsFeed(Feed):
    title = "Новости недвижимости"
    link = "/n/"
    description = "Последние новости о недвижимости"

    def items(self):
        return (
            NewsPage.objects.live()
            .select_related("author", "location", "main_image")
            .order_by("-first_published_at")[:20]
        )

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return strip_tags(str(item.intro))

    def item_link(self, item):
        return item.full_url

    def item_pubdate(self, item):
        return item.first_published_at