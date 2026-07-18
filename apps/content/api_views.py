from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Post
from .serializers import PostSerializer


class PostViewSet(viewsets.ReadOnlyModelViewSet):
    """Публичное REST API постов, включая результаты NLP-анализа (для внешних клиентов/JS-виджетов)."""

    queryset = (
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .select_related("author", "category", "analysis")
        .prefetch_related("tags", "entities")
    )
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = "slug"
