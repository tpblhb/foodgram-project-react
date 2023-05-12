from datetime import datetime
from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import BooleanField, Exists, OuterRef, Sum, Value
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response

from api.filters import IngredientSearchFilter, RecipeFilter
from api.paginations import Paginate
from api.permissions import IsAdminAuthorOrReadOnly, IsAdminOrReadOnly
from api.serializers import (
    FavoriteCheckingSerializer,
    FollowCheckSerializer,
    FollowSerializer,
    IngredientSerializer,
    RecipeAdditionSerializer,
    RecipeCreateSerializer,
    RecipeSerializer,
    ShoppingListCheckingSerializer,
    TagSerializer,
)
from recipes.models import (
    FavoriteRecipe,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)
from users.models import Follow

User = get_user_model()


class ListRetrieveViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
):
    permission_classes = (IsAdminOrReadOnly,)


class IngredientViewSet(ListRetrieveViewSet):
    pagination_class = None
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (IngredientSearchFilter,)
    search_fields = ('^name',)


class TagViewSet(ListRetrieveViewSet):
    pagination_class = None
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    pagination_class = Paginate
    permission_classes = (IsAdminAuthorOrReadOnly,)
    filter_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeSerializer
        return RecipeCreateSerializer

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Recipe.objects.annotate(
                is_favorited=Exists(
                    FavoriteRecipe.objects.filter(
                        user=self.request.user,
                        recipe__pk=OuterRef('pk'),
                    ),
                ),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(
                        user=self.request.user,
                        recipe__pk=OuterRef('pk'),
                    ),
                ),
            )
        else:
            return Recipe.objects.annotate(
                is_favorited=Value(False, output_field=BooleanField()),
                is_in_shopping_cart=Value(False, output_field=BooleanField()),
            )

    @transaction.atomic()
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated],
    )
    def favorite(self, request, pk=None):
        data = {
            'user': request.user.id,
            'recipe': pk,
        }
        serializer = FavoriteCheckingSerializer(
            data=data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        return self.add_object(FavoriteRecipe, request.user, pk)

    @favorite.mapping.delete
    def del_favorite(self, request, pk=None):
        data = {
            'user': request.user.id,
            'recipe': pk,
        }
        serializer = FavoriteCheckingSerializer(
            data=data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        return self.delete_object(FavoriteRecipe, request.user, pk)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated],
    )
    def shopping_cart(self, request, pk=None):
        data = {
            'user': request.user.id,
            'recipe': pk,
        }
        serializer = ShoppingListCheckingSerializer(
            data=data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        return self.add_object(ShoppingCart, request.user, pk)

    @shopping_cart.mapping.delete
    def remove_shopping_cart(self, request, pk=None):
        data = {
            'user': request.user.id,
            'recipe': pk,
        }
        serializer = ShoppingListCheckingSerializer(
            data=data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        return self.delete_object(ShoppingCart, request.user, pk)

    @transaction.atomic()
    def add_object(self, model, user, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        model.objects.create(user=user, recipe=recipe)
        serializer = RecipeAdditionSerializer(recipe)
        return Response(serializer.data, status=HTTPStatus.CREATED)

    @transaction.atomic()
    def delete_object(self, model, user, pk):
        model.objects.filter(user=user, recipe__id=pk).delete()
        return Response(status=HTTPStatus.NO_CONTENT)

    @action(
        methods=['get'],
        detail=False,
        permission_classes=[IsAuthenticated],
    )
    def download_shopping_cart(self, request):
        ingredients = (
            RecipeIngredient.objects.filter(
                recipe__cart__user=request.user,
            )
            .values(
                'ingredient__name',
                'ingredient__measurement_unit',
            )
            .annotate(quantity=Sum('amount'))
        )
        today = datetime.today()
        shopping = (
            f'Список покупок {request.user.username}\n'
            f'Дата: {today:%Y-%m-%d}\n\n'
        )
        shopping += '\n'.join(
            [
                f'- {ingredient["ingredient__name"]} '
                f'({ingredient["ingredient__measurement_unit"]})'
                f' - {ingredient["quantity"]}'
                for ingredient in ingredients
            ],
        )
        filename = f'{request.user.username}_shopping.txt'
        response = HttpResponse(shopping, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response


class FollowViewSet(UserViewSet):
    pagination_class = Paginate

    @action(
        methods=['post'],
        detail=True,
        permission_classes=[IsAuthenticated],
    )
    @transaction.atomic()
    def subscribe(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, pk=id)
        data = {
            'user': user.id,
            'author': author.id,
        }
        serializer = FollowCheckSerializer(
            data=data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        result = Follow.objects.create(user=user, author=author)
        serializer = FollowSerializer(result, context={'request': request})
        return Response(serializer.data, status=HTTPStatus.CREATED)

    @subscribe.mapping.delete
    @transaction.atomic()
    def del_subscribe(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, pk=id)
        data = {
            'user': user.id,
            'author': author.id,
        }
        serializer = FollowCheckSerializer(
            data=data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        user.follower.filter(author=author).delete()
        return Response(status=HTTPStatus.NO_CONTENT)

    @action(detail=False, permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        user = request.user
        queryset = user.follower.all()
        pages = self.paginate_queryset(queryset)
        serializer = FollowSerializer(
            pages,
            many=True,
            context={'request': request},
        )
        return self.get_paginated_response(serializer.data)
