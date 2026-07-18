# WP-Django — CMS-платформа (аналог WordPress) на Django

Production-скелет блоговой CMS с ИИ-обогащением контента:

- **Django 5 + PostgreSQL (pgvector) + Redis** — основной стек
- **Записи / Страницы / Категории / Теги / Комментарии / Медиатека / Роли пользователей** — как в WordPress
- **spaCy** — извлечение именованных сущностей (люди, организации, локации...) из текста поста
- **TextBlob** — тональность (полярность / субъективность)
- **sentence-transformers** — эмбеддинг текста, хранится в PostgreSQL через **pgvector**, используется для блока «Похожие записи» (косинусная близость)
- **Celery + Redis** — вся NLP-обработка выполняется асинхронно в воркере, не блокируя публикацию поста
- **Gunicorn + Nginx + Whitenoise** — production-раздача
- **Docker Compose** — полный продакшен-стек одной командой

## Структура

```
config/            # settings (base/development/production), celery, urls
apps/accounts/      # кастомный User с ролями (admin/editor/author/contributor/subscriber)
apps/content/        # Post, Page, Category, Tag, Comment, Media + views/urls/admin/REST API
apps/nlp/            # PostEntity, PostAnalysis(embedding: VectorField) + services.py + tasks.py
templates/           # HTML-шаблоны фронтенда
static/css/          # стили
nginx/, docker/       # конфиги для production
```

## Запуск в production (Docker)

1. Скопируйте `.env.example` в `.env` и заполните значения (SECRET_KEY, пароли БД, ALLOWED_HOSTS, домен и т.д.)
2. Соберите и поднимите стек:

   ```bash
   docker compose build
   docker compose up -d
   ```

   При старте контейнер `web` сам выполнит `migrate` и `collectstatic`. Расширение `vector` в PostgreSQL создаётся автоматически через `docker/init-pgvector.sql`.

3. Создайте суперпользователя:

   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

4. Сайт доступен на порту 80 (через Nginx), админка — `/admin/`.

Воркер `celery_worker` подхватывает NLP-обработку постов при публикации (сигнал `post_save` в `apps/content/signals.py`), `celery_beat` — периодический пересчёт "устаревших" эмбеддингов.

## Локальная разработка без Docker

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m spacy download ru_core_news_sm
python -m textblob.download_corpora

export DJANGO_SETTINGS_MODULE=config.settings.development
cp .env.example .env   # укажите свои POSTGRES_*/REDIS_URL для локальной БД

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

В dev-режиме `CELERY_TASK_ALWAYS_EAGER=True` по умолчанию — NLP-пайплайн выполняется синхронно, отдельный воркер не нужен.

## Как работает NLP-пайплайн

1. Пользователь публикует пост (статус `published`) в админке или через `post.publish()`.
2. Сигнал `post_save` (`apps/content/signals.py`) ставит задачу `process_post_nlp` в очередь Celery.
3. Задача (`apps/nlp/tasks.py`) вызывает `NLPPipeline.process()` из `apps/nlp/services.py`:
   - `EntityExtractor` (spaCy, модель `ru_core_news_sm`) → сохраняет `PostEntity`
   - `SentimentAnalyzer` (TextBlob) → `PostAnalysis.sentiment_polarity/subjectivity`
   - `Embedder` (`sentence-transformers`, модель `paraphrase-multilingual-MiniLM-L12-v2`, 384 измерения) → `PostAnalysis.embedding` (тип `vector` в PostgreSQL, индекс HNSW с cosine-метрикой)
4. На странице поста выводится тональность, найденные сущности и блок «Похожие записи», построенный запросом `CosineDistance` из `pgvector.django`.

> **Важно про язык:** TextBlob "из коробки" рассчитан на английский текст — точность тональности для русского контента будет ограниченной. В `apps/nlp/services.py` интерфейс `SentimentAnalyzer.analyze()` спроектирован так, чтобы легко заменить его на модель на основе transformers (например, `blanchefort/rubert-base-cased-sentiment`) без изменений в остальном коде.

## REST API

`GET /api/posts/` и `/api/posts/<slug>/` — отдаёт посты вместе с результатами NLP-анализа (сущности, тональность) в JSON, удобно для SPA/мобильных клиентов.

## Что можно добавить дальше

- Полнотекстовый поиск через `django.contrib.postgres.search` (SearchVector) в дополнение к векторному поиску
- WYSIWYG-редактор (например, django-ckeditor5) вместо простого textarea
- Кэширование списка постов и рендеринга в Redis (`django.core.cache`)
- Учёт версий/ревизий постов (как WordPress Revisions)
- S3-совместимое хранилище для медиа (django-storages) вместо локального volume
