from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse

from .forms import CommentForm
from .models import Category, Page, Post, Tag

def health_check(request):
    return JsonResponse({"status": "ok"})


def post_list(request):
    from .models import Page

    homepage = Page.objects.filter(is_homepage=True, status=Page.Status.PUBLISHED).first()
    if homepage:
        return render(request, "content/page_detail.html", {"page": homepage})
    
    posts = (
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .select_related("author", "category")
        .prefetch_related("tags")
    )

    query = request.GET.get("q")
    if query:
        posts = posts.filter(Q(title__icontains=query) | Q(content__icontains=query))

    category_slug = request.GET.get("category")
    if category_slug:
        posts = posts.filter(category__slug=category_slug)

    tag_slug = request.GET.get("tag")
    if tag_slug:
        posts = posts.filter(tags__slug=tag_slug)

    paginator_page = request.GET.get("page", 1)
    from django.core.paginator import Paginator

    paginator = Paginator(posts, 10)
    page_obj = paginator.get_page(paginator_page)

    return render(request, "content/post_list.html", {"page_obj": page_obj, "query": query or ""})


def post_detail(request, slug):
    post = get_object_or_404(
        Post.objects.select_related("author", "category", "analysis").prefetch_related("tags", "entities"),
        slug=slug,
        status=Post.Status.PUBLISHED,
    )

    Post.objects.filter(pk=post.pk).update(views_count=post.views_count + 1)

    comments = post.comments.filter(is_approved=True, parent__isnull=True).select_related("author").prefetch_related("replies")

    if request.method == "POST" and post.allow_comments:
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            if request.user.is_authenticated:
                comment.author = request.user
            # По умолчанию комментарии уходят на модерацию (как в WordPress)
            comment.is_approved = request.user.is_authenticated and request.user.can_moderate_comments()
            comment.save()
            messages.success(request, "Комментарий отправлен и ожидает модерации." if not comment.is_approved else "Комментарий добавлен.")
            return redirect(post.get_absolute_url())
    else:
        form = CommentForm()

    context = {
        "post": post,
        "comments": comments,
        "form": form,
        "related_posts": get_similar_posts(post),
    }
    return render(request, "content/post_detail.html", context)


def get_similar_posts(post, limit=4):
    """
    Похожие посты через косинусное расстояние в pgvector.
    Требует, чтобы у post.analysis.embedding был рассчитан эмбеддинг.
    """
    from pgvector.django import CosineDistance

    from apps.nlp.models import PostAnalysis

    analysis = getattr(post, "analysis", None)
    if not analysis or analysis.embedding is None:
        return Post.objects.none()

    similar_analyses = (
        PostAnalysis.objects.exclude(post=post)
        .filter(post__status=Post.Status.PUBLISHED, embedding__isnull=False)
        .annotate(distance=CosineDistance("embedding", analysis.embedding))
        .order_by("distance")
        .select_related("post")[:limit]
    )
    return [a.post for a in similar_analyses]


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    posts = Post.objects.filter(status=Post.Status.PUBLISHED, category=category)
    return render(request, "content/post_list.html", {"page_obj": posts, "category": category})


def tag_detail(request, slug):
    tag = get_object_or_404(Tag, slug=slug)
    posts = Post.objects.filter(status=Post.Status.PUBLISHED, tags=tag)
    return render(request, "content/post_list.html", {"page_obj": posts, "tag": tag})


def page_detail(request, slug):
    page = get_object_or_404(Page, slug=slug, status=Page.Status.PUBLISHED)
    return render(request, "content/page_detail.html", {"page": page})


@login_required
@require_http_methods(["POST"])
def moderate_comment(request, comment_id):
    from .models import Comment

    if not request.user.can_moderate_comments():
        messages.error(request, "Недостаточно прав.")
        return redirect("post_list")

    comment = get_object_or_404(Comment, pk=comment_id)
    action = request.POST.get("action")
    if action == "approve":
        comment.is_approved = True
        comment.save(update_fields=["is_approved"])
    elif action == "delete":
        comment.delete()
    return redirect(comment.post.get_absolute_url() if action != "delete" else "post_list")
