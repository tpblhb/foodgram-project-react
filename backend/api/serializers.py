from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_base64.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from api.mixins import GetIngredientsMixin, GetIsSubscribedMixin
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


class CustomUserCreateSerializer(UserCreateSerializer):
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all())],
    )
    username = serializers.CharField(
        validators=[UniqueValidator(queryset=User.objects.all())],
    )
    first_name = serializers.CharField()
    last_name = serializers.CharField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password',
        )


class CustomUserSerializer(GetIsSubscribedMixin, UserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
        )
        read_only_fields = ('is_subscribed',)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class RecipeSerializer(GetIngredientsMixin, serializers.ModelSerializer):
    tags = TagSerializer(many=True)
    author = CustomUserSerializer()
    ingredients = serializers.SerializerMethodField()
    is_favorited = serializers.BooleanField(default=False)
    is_in_shopping_cart = serializers.BooleanField(default=False)

    class Meta:
        model = Recipe
        fields = '__all__'


class RecipeIngredientsWriteSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField()


class RecipeCreateSerializer(GetIngredientsMixin, serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
    )
    ingredients = RecipeIngredientsWriteSerializer(many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = '__all__'
        read_only_fields = ('author',)

    def to_representation(self, instance):
        return RecipeSerializer(
            instance,
            context=self.context,
        ).data

    def validate(self, data):
        ingredients = data.get('ingredients')
        ingredient_list = []
        if not ingredients:
            raise serializers.ValidationError(
                'Должен быть хотя бы один ингредиент.',
            )
        for item in ingredients:
            ingredient = get_object_or_404(
                Ingredient,
                id=item['id'],
            )
            if ingredient in ingredient_list:
                raise serializers.ValidationError(
                    'Этот ингредиент уже есть',
                )
            if int(item['amount']) < 1:
                raise serializers.ValidationError(
                    'Минимум - 1',
                )
            ingredient_list.append(ingredient)
        return data

    def validate_cooking_time(self, time):
        if int(time) < 1:
            raise serializers.ValidationError(
                'Минимальное время = 1',
            )
        return time

    def add_ingredients_and_tags(self, instance, **validate_data):
        ingredients = validate_data['ingredients']
        tags = validate_data['tags']
        for tag in tags:
            instance.tags.add(tag)

        RecipeIngredient.objects.bulk_create(
            [
                RecipeIngredient(
                    recipe=instance,
                    ingredient_id=ingredient.get('id'),
                    amount=ingredient.get('amount'),
                )
                for ingredient in ingredients
            ],
        )
        return instance

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = super().create(validated_data)
        return self.add_ingredients_and_tags(
            recipe,
            ingredients=ingredients,
            tags=tags,
        )

    def update(self, instance, validated_data):
        instance.ingredients.clear()
        instance.tags.clear()
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance = self.add_ingredients_and_tags(
            instance,
            ingredients=ingredients,
            tags=tags,
        )
        return super().update(instance, validated_data)


class RecipeAdditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('id', 'name', 'image', 'cooking_time')


class FollowSerializer(GetIsSubscribedMixin, serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='author.id')
    email = serializers.ReadOnlyField(source='author.email')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = Follow
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        queryset = obj.author.recipes.all()
        if limit:
            queryset = queryset[: int(limit)]
        return RecipeAdditionSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        return obj.author.recipes.all().count()


class FollowCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = ('user', 'author')

    def validate_follows(self, obj):
        user = obj['user']
        author = obj['author']
        subscribed = user.follower.filter(author=author).exists()

        if self.context.get('request').method == 'POST':
            if subscribed:
                raise serializers.ValidationError(
                    'Вы уже подписаны',
                )
            if user == author:
                raise serializers.ValidationError(
                    'Нельзя подписаться на самого себя',
                )
        if self.context.get('request').method == 'DELETE':
            if not subscribed:
                raise serializers.ValidationError(
                    'Вы уже отписаны',
                )
            if user == author:
                raise serializers.ValidationError(
                    'Нельзя отписаться от самого себя',
                )
        return obj


class FavoriteCheckingSerializer(serializers.ModelSerializer):
    recipe = serializers.PrimaryKeyRelatedField(
        queryset=Recipe.objects.all(),
    )
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
    )

    class Meta:
        model = FavoriteRecipe
        fields = ('user', 'recipe')

    def validate_favorites(self, obj):
        user = self.context['request'].user
        recipe = obj['recipe']
        favorite = user.favorites.filter(recipe=recipe).exists()

        if self.context.get('request').method == 'POST' and favorite:
            raise serializers.ValidationError(
                'Этот рецепт уже в избранных',
            )
        if self.context.get('request').method == 'DELETE' and not favorite:
            raise serializers.ValidationError(
                'Этого рецепта уже нет в избранных',
            )
        return obj


class ShoppingListCheckingSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
    )
    recipe = serializers.PrimaryKeyRelatedField(
        queryset=Recipe.objects.all(),
    )

    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')

    def validate_shopping_list(self, obj):
        user = self.context['request'].user
        recipe = obj['recipe']
        cart = user.cart.filter(recipe=recipe).exists()

        if self.context.get('request').method == 'POST' and cart:
            raise serializers.ValidationError(
                'Ингредиенты из этого рецепта уже в корзине',
            )
        if self.context.get('request').method == 'DELETE' and not cart:
            raise serializers.ValidationError(
                'Ингредиентов из этого рецепта уже нет в корзине',
            )
        return obj
