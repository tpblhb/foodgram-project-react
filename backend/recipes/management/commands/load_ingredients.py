from csv import DictReader

from django.core.management import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка из csv файла'

    def handle(self, *args, **kwargs):
        if Ingredient.objects.exists():
            print('В базу уже загружены данные.')
            return
        try:
            with open(
                './data/ingredients.csv',
                'r',
                encoding='utf-8',
            ) as file:
                reader = DictReader(file)
                Ingredient.objects.bulk_create(
                    Ingredient(**data) for data in reader
                )
        except ValueError:
            print('Неопределенное значение.')
        else:
            print('Ингредиенты загружены.')
