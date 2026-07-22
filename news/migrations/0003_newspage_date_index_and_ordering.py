from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0002_newspage_source_name_newspage_source_url_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='newspage',
            options={'ordering': ['-date']},
        ),
        migrations.AlterField(
            model_name='newspage',
            name='date',
            field=models.DateField(db_index=True, verbose_name='Дата публикации'),
        ),
    ]
