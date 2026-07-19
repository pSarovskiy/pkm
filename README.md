# Wagtail CMS + PostgreSQL/pgvector + Redis + NLP-пайплайн

Production-конфигурация сайта на [Wagtail CMS](https://wagtail.org/) в Docker,
с поддержкой live-редактирования файлов на Windows, PostgreSQL с расширением
`pgvector`, Redis, и асинхронным NLP-пайплайном:

- **spaCy** — извлечение именованных сущностей (люди, организации, места и т.д.);
- **TextBlob** — анализ тональности текста (`polarity`/`subjectivity`);
- **sentence-transformers** — превращение текста страницы в эмбеддинг (вектор),
  который сохраняется в PostgreSQL через `pgvector` и используется для поиска
  семантически похожих страниц.

Обработка запускается автоматически при публикации страницы в админке
Wagtail и выполняется в фоне через Celery-воркер, не блокируя сохранение.

---

## 1. Структура проекта

```
.
├── docker-compose.yml          # РАЗРАБОТКА: bind-mount исходников, runserver
├── docker-compose.prod.yml     # PRODUCTION: gunicorn + nginx, без bind-mount
├── Dockerfile                  # Двухстадийная сборка, модели NLP качаются при сборке
├── .env.example                # Шаблон переменных окружения -> скопировать в .env
├── docker/
│   ├── entrypoint.dev.sh       # dev: ждёт БД, миграции, затем runserver
│   ├── entrypoint.prod.sh      # prod: ждёт БД, миграции, collectstatic, gunicorn
│   ├── init-pgvector.sql       # CREATE EXTENSION vector при первом старте БД
│   └── nginx/nginx.conf        # Реверс-прокси + отдача static/media
├── myproject/                  # Django/Wagtail-проект (settings, celery.py, urls.py)
│   └── settings/
│       ├── base.py             # Общие настройки, БД, Redis, Celery, NLP-параметры
│       ├── dev.py
│       └── production.py
├── home/                       # Пример приложения-страницы (HomePage с полем intro)
├── search/                     # Встроенный поиск Wagtail (из стартового шаблона)
└── nlp/                        # Приложение NLP-пайплайна
    ├── models.py                # PageAnalysis: entities, sentiment, embedding (pgvector)
    ├── services.py               # Логика spaCy / TextBlob / sentence-transformers
    ├── tasks.py                  # Celery-таск process_page_nlp
    ├── signals.py                 # Подписка на page_published
    ├── admin.py                   # Просмотр результатов в /django-admin/
    └── management/commands/reindex_nlp.py   # Батч-обработка всех страниц
```

---

## 2. Быстрый старт (Windows)

### Требования

- [Docker Desktop для Windows](https://www.docker.com/products/docker-desktop/)
  с включённым бэкендом **WSL 2** (рекомендуется Microsoft/Docker).
- Редактор кода (VS Code, PyCharm и т.д.) — можно редактировать файлы проекта
  прямо в Windows, без входа в контейнер.
- Git (желательно с настройкой `git config --global core.autocrlf false`,
  чтобы не ломать перенос строк в shell-скриптах — см. раздел 6).

### Шаги

1. Распакуйте проект в удобную папку, например `C:\projects\wagtail-site`.
2. Откройте PowerShell или терминал VS Code в этой папке.
3. Создайте файл окружения из шаблона:
   ```powershell
   copy .env.example .env
   ```
4. Откройте `.env` и задайте:
   - `DJANGO_SECRET_KEY` — любая длинная случайная строка;
   - `POSTGRES_PASSWORD` — пароль для базы данных;
   - при необходимости `NLP_SPACY_MODEL=ru_core_news_sm`, если контент сайта
     на русском (подробнее — раздел 5).
5. Соберите и запустите контейнеры:
   ```powershell
   docker compose up --build
   ```
   Первая сборка займёт заметное время: скачиваются base-образы Python/Postgres,
   Python-зависимости и NLP-модели (spaCy, sentence-transformers). Последующие
   запуски будут быстрыми за счёт кэша Docker.
6. В отдельном терминале создайте суперпользователя Wagtail:
   ```powershell
   docker compose exec web python manage.py createsuperuser
   ```
7. Откройте сайт: <http://localhost:8000/>, админку Wagtail:
   <http://localhost:8000/admin/>.

### Редактирование файлов в Windows

В dev-режиме (`docker-compose.yml`) вся папка проекта примонтирована в контейнер
(`.:/app`). Это значит:

- Любой файл — Python-код, HTML-шаблоны, `requirements.txt`, статику — можно
  редактировать прямо в Windows любым редактором.
- Изменения в `.py`/`.html` подхватываются немедленно: `runserver` Django
  перезапускается автоматически.
- Если вы изменили `requirements.txt` или `Dockerfile` — нужно пересобрать
  образ: `docker compose up --build`.
- Если вы изменили модели (`models.py`) — создайте и примените миграцию:
  ```powershell
  docker compose exec web python manage.py makemigrations
  docker compose exec web python manage.py migrate
  ```

---

## 3. NLP-пайплайн: как это работает

1. Редактор публикует страницу в админке Wagtail (`page_published`).
2. `nlp/signals.py` ставит в очередь Celery-задачу `process_page_nlp`
   (сервис `celery` в docker-compose, брокер — Redis).
3. `nlp/services.run_pipeline()`:
   - собирает текст страницы, обходя её `search_fields` (работает для любого
     типа страницы, не только `HomePage`);
   - извлекает сущности через spaCy (`nlp/services.extract_entities`);
   - считает тональность через TextBlob (`analyze_sentiment`);
   - строит эмбеддинг через sentence-transformers (`compute_embedding`);
   - сохраняет всё в `nlp.models.PageAnalysis`, включая `VectorField` в pgvector.
4. Результаты видны в стандартной Django-админке: `/django-admin/nlp/pageanalysis/`.

### Пакетная обработка всех уже существующих страниц

```powershell
docker compose exec web python manage.py reindex_nlp
# или асинхронно через Celery:
docker compose exec web python manage.py reindex_nlp --async
```

### Поиск похожих страниц по смыслу (semantic search)

```python
from nlp.services import find_similar_pages
similar = find_similar_pages(page, limit=5)  # QuerySet[PageAnalysis], ближайшие по cosine distance
```

---

## 4. Production-развёртывание

Production использует отдельный файл `docker-compose.prod.yml`: исходники
запекаются в образ на этапе сборки (никакого bind-mount), перед приложением
стоит nginx, статика и медиа лежат в именованных Docker-томах.

```bash
cp .env.example .env
# заполнить .env "боевыми" значениями:
#   DJANGO_SETTINGS_MODULE=myproject.settings.production
#   DJANGO_DEBUG=False
#   DJANGO_SECRET_KEY=<длинный случайный секрет>
#   DJANGO_ALLOWED_HOSTS=example.com,www.example.com
#   DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
#   POSTGRES_PASSWORD=<надёжный пароль>

docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

`docker/entrypoint.prod.sh` при каждом старте контейнера `web` автоматически:
дожидается доступности PostgreSQL → применяет миграции → выполняет
`collectstatic` → запускает `gunicorn`.

Сайт будет доступен на порту 80 (nginx). Для HTTPS поставьте перед nginx
обратный прокси/балансировщик с TLS-терминацией (например, Traefik,
Caddy или облачный балансировщик) — в `docker-compose.prod.yml` они
не включены намеренно, чтобы не привязывать конфигурацию к конкретному
провайдеру сертификатов.

### Бэкапы

```bash
# Дамп базы данных
docker compose -f docker-compose.prod.yml exec db pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql

# Восстановление
cat backup.sql | docker compose -f docker-compose.prod.yml exec -T db psql -U $POSTGRES_USER $POSTGRES_DB
```

---

## 5. Русскоязычный контент

По умолчанию используется английская модель spaCy `en_core_web_sm`. Для
русского языка:

1. В `.env` укажите:
   ```
   NLP_SPACY_MODEL=ru_core_news_sm
   ```
2. Пересоберите образ с тем же значением в build-arg (docker-compose уже
   подставляет его автоматически из `.env` через `${NLP_SPACY_MODEL:-...}`):
   ```powershell
   docker compose up --build
   ```

**Важно про TextBlob**: библиотека ориентирована на английский язык, её
встроенный анализатор тональности для русского текста будет давать
низкое качество результатов (это ограничение самой библиотеки, а не
конфигурации). Если тональность русскоязычного контента критична для
задачи, в перспективе стоит заменить `analyze_sentiment()` в
`nlp/services.py` на модель из HuggingFace, обученную на русском
(например, любую `*-sentiment-ru` модель) — точка расширения уже
изолирована в одной функции.

`sentence-transformers` модель по умолчанию (`all-MiniLM-L6-v2`)
многоязычная в базовой мере, но для качественных русскоязычных
эмбеддингов лучше использовать `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
(тогда не забудьте поменять `NLP_EMBEDDING_DIMENSIONS`, если размерность
вектора отличается, и совпадающим образом обновить `dimensions=` в
`nlp/models.py` + создать новую миграцию).

---

## 6. Частые проблемы на Windows

- **`entrypoint.dev.sh: bad interpreter` / контейнер сразу падает.**
  Обычно это Windows-переносы строк `\r\n` в shell-скрипте после
  сохранения файла каким-то редактором. В репозитории уже есть
  `.gitattributes` с `eol=lf` для `*.sh`, но если вы копировали
  проект не через `git clone`, а вручную (например, распаковали zip
  и правили в блокноте) — проверьте окончания строк вручную (в VS Code:
  нижний правый угол, `CRLF` → сменить на `LF`).

- **Медленная файловая система / долгий старт `runserver`.**
  Убедитесь, что папка проекта находится не на диске, синхронизируемом
  OneDrive, и что Docker Desktop использует бэкенд **WSL 2**
  (Settings → General → "Use the WSL 2 based engine"). Ещё быстрее —
  держать исходники внутри WSL-файловой системы (`\\wsl$\...`), а не на `C:\`.

- **Порт 8000 (или 5432/6379) уже занят.**
  Поменяйте маппинг портов в `docker-compose.yml`, например
  `"8080:8000"` вместо `"8000:8000"`.

- **`docker compose exec web ...` говорит "no such service".**
  Убедитесь, что вы находитесь в папке проекта и что контейнеры подняты
  (`docker compose ps`).

---

## 7. Переменные окружения

Полный список — в `.env.example`. Ключевые:

| Переменная | Назначение |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `myproject.settings.dev` или `myproject.settings.production` |
| `DJANGO_SECRET_KEY` | секретный ключ Django, обязателен в production |
| `POSTGRES_*` | параметры подключения к БД |
| `REDIS_URL` / `CELERY_*` | Redis как кэш и брокер Celery |
| `NLP_SPACY_MODEL` | модель spaCy для NER (`en_core_web_sm` / `ru_core_news_sm`) |
| `NLP_EMBEDDING_MODEL` | модель sentence-transformers для эмбеддингов |
| `NLP_EMBEDDING_DIMENSIONS` | размерность вектора; должна совпадать с `dimensions=` в `nlp/models.py` |
