import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('news', '0003_newspage_date_index_and_ordering'),
    ]

    operations = [
        migrations.AddField(
            model_name='author',
            name='user',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='author_profile',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Связанный аккаунт CMS',
                help_text=(
                    'Если заполнено — этот автор будет автоматически подставляться '
                    'в новых постах, которые создаёт этот пользователь.'
                ),
            ),
        ),
    ]
