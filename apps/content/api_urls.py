from rest_framework.routers import DefaultRouter

from .api_views import PostViewSet

router = DefaultRouter()
router.register("posts", PostViewSet, basename="api-post")

urlpatterns = router.urls
