from rest_framework import serializers
from django.db import transaction
from . import models as m

class OwnedSerializer(serializers.ModelSerializer):
    def get_fields(self):
        fields = super().get_fields()
        for name in ('outfit', 'items'):
            field = fields.get(name)
            if field is not None:
                target = field.child_relation if isinstance(field, serializers.ManyRelatedField) else field
                if target.queryset is not None:
                    target.queryset = target.queryset.filter(user=self.context['request'].user)
        return fields

class ProfileSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        if self.instance and 'city' in attrs and attrs['city'] != self.instance.city and 'latitude' not in attrs and 'longitude' not in attrs:
            attrs['latitude'] = None
            attrs['longitude'] = None
        latitude = attrs.get('latitude', self.instance.latitude if self.instance else None)
        longitude = attrs.get('longitude', self.instance.longitude if self.instance else None)
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError('Укажите либо очистите обе координаты.')
        return attrs

    avatar = serializers.SerializerMethodField()
    def get_avatar(self, obj):
        from .photos import metadata
        return metadata(obj.avatar, '/api/profile/avatar/') if hasattr(obj, 'avatar') else None

    class Meta:
        model = m.UserProfile
        fields = ['id','display_name','preferred_style','city','cold_sensitivity','heat_sensitivity','avatar','latitude','longitude']
        read_only_fields = ['id']

class StyleListField(serializers.ListField):
    def __init__(self, **kwargs):
        super().__init__(child=serializers.CharField(max_length=80, allow_blank=False), max_length=20, **kwargs)

    def to_internal_value(self, data):
        values = super().to_internal_value(data)
        if len({value.casefold() for value in values}) != len(values):
            raise serializers.ValidationError('Styles must be unique.')
        return values

class ClothingItemSerializer(OwnedSerializer):
    category_slot = serializers.CharField(source='category.slot', read_only=True)
    photo = serializers.SerializerMethodField()
    def get_photo(self, obj):
        from .photos import metadata
        return metadata(obj.photo, f'/api/clothing/{obj.pk}/photo/') if hasattr(obj, 'photo') else None

    styles = StyleListField(required=False)
    class Meta:
        model = m.ClothingItem
        fields = ['id','name','category','colors','description','season','is_available','brand','material','fit','styles','created_at','updated_at','photo','comfort','warmth','category_slot']
        read_only_fields = ['id','created_at','updated_at']

class OutfitSerializer(OwnedSerializer):
    generation_is_stale = serializers.SerializerMethodField()
    def get_generation_is_stale(self, obj):
        if not obj.generation:
            return False
        versions = {str(item.pk):item.updated_at.isoformat() for item in obj.items.all()}
        return versions != obj.generation.get('item_versions', {})

    item_details = ClothingItemSerializer(source="items", many=True, read_only=True)
    items = serializers.PrimaryKeyRelatedField(many=True, queryset=m.ClothingItem.objects.all())
    def validate_items(self, items):
        if len({i.pk for i in items}) != len(items):
            raise serializers.ValidationError('Duplicate clothing items.')
        return items
    @transaction.atomic
    def create(self, validated_data):
        return super().create(validated_data)
    @transaction.atomic
    def update(self, instance, validated_data):
        if 'items' in validated_data:
            validated_data['generation'] = {}
        return super().update(instance, validated_data)
    class Meta:
        model = m.Outfit
        fields = ['id','name','items','item_details','created_at','generation','generation_is_stale']
        read_only_fields = ['id','created_at','generation']

class OutfitItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = m.OutfitItem
        fields = ['id','clothing_item']
        read_only_fields = fields

class PreferenceSerializer(serializers.ModelSerializer):
    styles = StyleListField(required=False)

    def validate(self, attrs):
        def color_ids(name):
            if name in attrs:
                return {color.pk for color in attrs[name]}
            return set(getattr(self.instance, name).values_list('pk', flat=True)) if self.instance else set()
        if color_ids('preferred_colors') & color_ids('disliked_colors'):
            raise serializers.ValidationError({'disliked_colors': 'A color cannot be both preferred and disliked.'})
        return attrs

    class Meta:
        model = m.OutfitPreference
        fields = ['id','style','styles','preferred_colors','disliked_colors','preferred_fit','comfort_priority','excluded_categories']
        read_only_fields = ['id']

class FeedbackSerializer(OwnedSerializer):
    class Meta:
        model = m.OutfitFeedback
        fields = ['id','outfit','rating','comment','created_at']
        read_only_fields = ['id','created_at']
        validators = []
    def validate(self, attrs):
        outfit = attrs.get('outfit', getattr(self.instance,'outfit',None))
        qs = m.OutfitFeedback.objects.filter(user=self.context['request'].user,outfit=outfit)
        if self.instance: qs = qs.exclude(pk=self.instance.pk)
        if qs.exists(): raise serializers.ValidationError('Feedback already exists.')
        return attrs

class SavedSerializer(FeedbackSerializer):
    class Meta:
        model = m.SavedOutfit
        fields = ['id','outfit','created_at']
        read_only_fields = ['id','created_at']
        validators = []
    def validate(self, attrs):
        outfit = attrs.get('outfit', getattr(self.instance,'outfit',None))
        qs = m.SavedOutfit.objects.filter(user=self.context['request'].user,outfit=outfit)
        if self.instance: qs = qs.exclude(pk=self.instance.pk)
        if qs.exists(): raise serializers.ValidationError('Outfit already saved.')
        return attrs

class WeatherSerializer(OwnedSerializer):
    class Meta:
        model = m.WeatherContext
        fields = ['id','latitude','longitude','temperature_c','condition','observed_at','created_at','apparent_temperature_c','precipitation_probability','wind_speed_kmh','forecast_for','source']
        read_only_fields = fields

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = m.ClothingCategory
        fields = ['id','name','slot']

class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = m.ClothingColor
        fields = ['id','name','hex_code']


class CalendarSerializer(OwnedSerializer):
    outfit_details = OutfitSerializer(source='outfit', read_only=True)
    class Meta:
        model = m.OutfitCalendarEntry
        fields = ['id','outfit','outfit_details','date','note','created_at']
        read_only_fields = ['id','created_at']
        validators = []
    def validate(self, attrs):
        date = attrs.get('date', self.instance.date if self.instance else None)
        qs = m.OutfitCalendarEntry.objects.filter(user=self.context['request'].user,date=date)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError({'date':'На эту дату уже запланирован образ.'})
        return attrs
