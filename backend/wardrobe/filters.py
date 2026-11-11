"""Validated collection filters applied after the owner restriction."""
from django.db.models import Q
from rest_framework import serializers
from .models import ClothingItem, ClothingCategory


class ClothingQuerySerializer(serializers.Serializer):
    search = serializers.CharField(max_length=150, required=False, allow_blank=True)
    category = serializers.IntegerField(min_value=1, required=False)
    color = serializers.IntegerField(min_value=1, required=False)
    slot = serializers.ChoiceField(choices=ClothingCategory._meta.get_field('slot').choices, required=False)
    season = serializers.ChoiceField(choices=ClothingItem._meta.get_field('season').choices, required=False)
    is_available = serializers.BooleanField(required=False)
    fit = serializers.ChoiceField(choices=ClothingItem._meta.get_field('fit').choices, required=False)
    ordering = serializers.ChoiceField(choices=['name', '-name', 'created_at', '-created_at', 'updated_at', '-updated_at'], required=False, default='-created_at')


def filter_clothing(queryset, params):
    allowed = set(ClothingQuerySerializer().fields) | {'page', 'format'}
    unknown = set(params) - allowed
    if unknown:
        raise serializers.ValidationError({key: 'Unknown filter.' for key in sorted(unknown)})
    repeated = [key for key in params if len(params.getlist(key)) > 1]
    if repeated:
        raise serializers.ValidationError({key: 'Supply one value.' for key in repeated})
    # Query parameters are not an HTML checkbox form: absent booleans must stay absent.
    serializer = ClothingQuerySerializer(data=params.dict())
    serializer.is_valid(raise_exception=True)
    values = serializer.validated_data
    search = values.get('search')
    if search:
        queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search) | Q(brand__icontains=search))
    for key, lookup in [('category', 'category_id'), ('color', 'colors__id'), ('slot', 'category__slot'), ('season', 'season'), ('is_available', 'is_available'), ('fit', 'fit')]:
        if key in values:
            queryset = queryset.filter(**{lookup: values[key]})
    return queryset.order_by(values['ordering'], 'pk')
