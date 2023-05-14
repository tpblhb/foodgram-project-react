# Foodgram-project-react

## Описание

Это дипломный проект - сайт Foodgram, «Продуктовый помощник». На этом сервисе пользователи могут публиковать рецепты, подписываться на публикации других пользователей, добавлять понравившиеся рецепты в список «Избранное», а перед походом в магазин скачивать сводный список продуктов, необходимых для приготовления одного или нескольких выбранных блюд.

## Технологии

Python, Django, Docker

## Шаблон наполнения .env файла

```bash
DB_ENGINE=django.db.backends.postgresql
DB_HOST=127.0.0.1
DB_NAME=foodgramdb
DB_PORT=5432
DEBUG=False
POSTGRES_PASSWORD=shish123
POSTGRES_USER=shish
SECRET_KEY='p&l%385148kslhtyn^##a1)ilz@4zqj=rq&agdol^##zgl9(vs'
```

## Запуск

Пройтись по разделам для сборки docker-compose.

```bash
cd frontend/
docker build -t tpblhb/food_frontend .
cd ../backend/
docker build -t tpblhb/food_backend .
cd ../infra/
docker-compose up -d --build
```

Выполнить миграции

```bash
docker-compose exec backend python manage.py makemigrations
docker-compose exec backend python manage.py migrate
```

Создать суперпользователя

```bash
docker-compose exec backend python manage.py createsuperuser
```

Сформировать STATIC файлы:

```bash
docker-compose exec backend python manage.py collectstatic --no-input
```

Загрузить тэги и ингредиенты:

```bash
docker-compose exec backend python manage.py load_tags
docker-compose exec backend python manage.py load_ingredients
```

## Автор

Шишкин Александр, студент яндекс.практикум, когорта 49
