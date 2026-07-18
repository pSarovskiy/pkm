from django.urls import path

from . import views

urlpatterns = [
    path("", views.post_list, name="post_list"),
    path('health/', views.health_check, name='health_check'),
    path("category/<slug:slug>/", views.category_detail, name="category_detail"),
    path("tag/<slug:slug>/", views.tag_detail, name="tag_detail"),
    path("comments/<int:comment_id>/moderate/", views.moderate_comment, name="moderate_comment"),
    path("<slug:slug>/", views.post_detail, name="post_detail"),
    path("page/<slug:slug>/", views.page_detail, name="page_detail"),
]
