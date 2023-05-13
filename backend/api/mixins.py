from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
)
from rest_framework.viewsets import ModelViewSet

from recipes.models import Recipe


class GetIsSubscribedMixin:
    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return user.follower.filter(author=obj.id).exists()


class GetIngredientsMixin:
    def get_ingredients(self, obj):
        return obj.ingredients.values(
            'id',
            'name',
            'measurement_unit',
            amount=F('quantity_ingredients__amount'),
        )


class AddRemoveMethod(ModelViewSet):
    def _add_method(self, request, pk, serializers):
        data = {'user': request.user.id, 'recipe': pk}
        serializer = serializers(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=HTTP_201_CREATED)

    def _remove_method(self, request, pk, model):
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)
        model_obj = model.objects.filter(user=user, recipe=recipe)
        if model_obj.exists():
            model_obj.delete()
            return Response(status=HTTP_204_NO_CONTENT)
        return Response(
            {'error': 'Этого рецепта уже нет'},
            status=HTTP_400_BAD_REQUEST,
        )
