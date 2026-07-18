from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Пользователь с ролями в стиле WordPress:
    Administrator / Editor / Author / Contributor / Subscriber.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Администратор"
        EDITOR = "editor", "Редактор"
        AUTHOR = "author", "Автор"
        CONTRIBUTOR = "contributor", "Внештатный автор"
        SUBSCRIBER = "subscriber", "Подписчик"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SUBSCRIBER)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    website = models.URLField(blank=True)

    def can_publish(self) -> bool:
        return self.is_superuser or self.role in {self.Role.ADMIN, self.Role.EDITOR, self.Role.AUTHOR}

    def can_moderate_comments(self) -> bool:
        return self.is_superuser or self.role in {self.Role.ADMIN, self.Role.EDITOR}

    def __str__(self):
        return self.get_full_name() or self.username
