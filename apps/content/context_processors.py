from django.conf import settings

from .models import Category


def site_meta(request):
    current_category_slug = None

    if request.resolver_match:
        if request.resolver_match.url_name == "category_detail":
            current_category_slug = request.resolver_match.kwargs.get("slug")
        elif request.resolver_match.url_name == "post_detail":
            slug = request.resolver_match.kwargs.get("slug")
            from .models import Post
            post = Post.objects.filter(slug=slug).select_related("category").first()
            if post and post.category:
                current_category_slug = post.category.slug

    return {
        "SITE_NAME": settings.SITE_NAME,
        "nav_categories": Category.objects.filter(parent__isnull=True).order_by("name")[:10],
        "current_category_slug": current_category_slug,
    }
