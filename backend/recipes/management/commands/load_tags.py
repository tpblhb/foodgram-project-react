from django.core.management import BaseCommand

from recipes.models import Tag


class Command(BaseCommand):
    help = 'Создание тэгов.'

    def handle(self, *args, **kwargs):
        data = [
            {'name': 'Завтрак', 'color': '#5E9653', 'slug': 'breakfast'},
            {'name': 'Обед', 'color': '#965D3E', 'slug': 'lunch'},
            {'name': 'Ужин', 'color': '#7F3E96', 'slug': 'dinner'},
            {'name': 'Закуска', 'color': '#AFB84B', 'slug': 'snack'},
        ]
        try:
            Tag.objects.bulk_create(Tag(**tag) for tag in data)
        except ValueError:
            print('Неопределенное значение.')
        except Exception:
            print('Что-то пошло не так!')
        else:
            print('Тэги загружены.')
