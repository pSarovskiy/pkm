from rest_framework import serializers

from .models import Category, Post, Tag


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]


class PostSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    author = serializers.StringRelatedField()
    sentiment = serializers.SerializerMethodField()
    entities = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id", "title", "slug", "excerpt", "content", "author",
            "category", "tags", "published_at", "views_count",
            "sentiment", "entities",
        ]

    def get_sentiment(self, obj):
        analysis = getattr(obj, "analysis", None)
        if not analysis:
            return None
        return {
            "polarity": analysis.sentiment_polarity,
            "subjectivity": analysis.sentiment_subjectivity,
            "label": analysis.sentiment_label,
        }

    def get_entities(self, obj):
        return [{"text": e.text, "label": e.label} for e in obj.entities.all()]
