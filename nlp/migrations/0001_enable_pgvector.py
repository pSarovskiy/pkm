from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):
    """
    Enables the PostgreSQL `vector` extension (provided by the pgvector
    image, see docker/init-pgvector.sql) so that VectorField / HnswIndex
    can be used by the models created in the next migration.
    """

    initial = True

    dependencies = []

    operations = [
        VectorExtension(),
    ]
