from django.db import transaction
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import ClothingItem, Outfit, OutfitItem, OutfitPreference, UserProfile
from .serializers import OutfitSerializer
from .generator import generate
from .weather_api import CoordinatesSerializer, AwareDateTimeField
from .services import weather
from .services.http import ServiceUnavailable


class WeightsSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, dict) and set(data) - set(self.fields):
            raise serializers.ValidationError('Неизвестный критерий веса.')
        return super().to_internal_value(data)

    comfort = serializers.IntegerField(min_value=0, max_value=100)
    weather = serializers.IntegerField(min_value=0, max_value=100)
    style = serializers.IntegerField(min_value=0, max_value=100)
    colors = serializers.IntegerField(min_value=0, max_value=100)
    preferences = serializers.IntegerField(min_value=0, max_value=100)

    def validate(self, attrs):
        if sum(attrs.values()) != 100:
            raise serializers.ValidationError('Сумма весов должна быть равна 100.')
        return attrs


class GenerationSerializer(serializers.Serializer):
    use_weather = serializers.BooleanField(default=False)
    weather_location = CoordinatesSerializer(required=False)
    forecast_at = AwareDateTimeField(required=False)
    weather_failure = serializers.ChoiceField(choices=['continue','abort'], default='continue')
    count = serializers.IntegerField(min_value=3, max_value=5, default=3)
    occasion = serializers.ChoiceField(choices=['everyday','university','work','sport','party','formal'], default='everyday')
    style = serializers.CharField(max_length=80, required=False, allow_blank=True)
    comfort_priority = serializers.IntegerField(min_value=0, max_value=100, required=False)
    season = serializers.ChoiceField(choices=['all','summer','winter','spring','autumn'], default='all')
    temperature_c = serializers.FloatField(min_value=-60, max_value=60, required=False)
    required_items = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=6, default=list)
    excluded_items = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=500, default=list)
    preferred_colors = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=30, required=False)
    notes = serializers.CharField(max_length=1000, allow_blank=True, default='')
    weights = WeightsSerializer(required=False)

    def validate(self, attrs):
        unknown = set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({key:'Неизвестный параметр.' for key in sorted(unknown)})
        for key in ['required_items','excluded_items','preferred_colors']:
            if key in attrs and len(attrs[key]) != len(set(attrs[key])):
                raise serializers.ValidationError({key:'ID не должны повторяться.'})
        if set(attrs['required_items']) & set(attrs['excluded_items']):
            raise serializers.ValidationError('Вещь не может быть обязательной и исключённой одновременно.')
        if 'temperature_c' in attrs:
            import math
            if not math.isfinite(attrs['temperature_c']):
                raise serializers.ValidationError({'temperature_c':'Нужно конечное число.'})
        if attrs.get('use_weather') and 'temperature_c' in attrs:
            raise serializers.ValidationError('Выберите автоматическую погоду или ручную температуру.')
        if not attrs.get('use_weather') and ('weather_location' in attrs or 'forecast_at' in attrs):
            raise serializers.ValidationError('Для запроса прогноза укажите use_weather=true.')
        if 'forecast_at' in attrs:
            from datetime import timedelta
            from django.utils import timezone
            if not timezone.now()-timedelta(hours=1) <= attrs['forecast_at'] <= timezone.now()+timedelta(days=6):
                raise serializers.ValidationError({'forecast_at':'Прогноз доступен до шести дней вперёд.'})
            attrs['forecast_at'] = attrs['forecast_at'].isoformat()
        if 'weather_location' in attrs:
            attrs['weather_location'] = {key:float(value) for key,value in attrs['weather_location'].items()}
        from .models import ClothingColor
        if 'preferred_colors' in attrs and ClothingColor.objects.filter(pk__in=attrs['preferred_colors']).count() != len(attrs['preferred_colors']):
            raise serializers.ValidationError({'preferred_colors':'Неизвестный цвет.'})
        return attrs


class GenerateOutfitsView(APIView):
    def post(self, request):
        serializer = GenerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        options = serializer.validated_data
        weather_data = None
        weather_message = None
        if options['use_weather']:
            profile = UserProfile.objects.filter(user=request.user).first()
            location = options.get('weather_location')
            if location is None and profile and profile.latitude is not None and profile.longitude is not None:
                location = {'latitude':profile.latitude,'longitude':profile.longitude}
            try:
                if location is None:
                    raise ServiceUnavailable('Сначала выберите координаты города в профиле или запросе.')
                from datetime import datetime
                at = datetime.fromisoformat(options['forecast_at']) if options.get('forecast_at') else None
                weather_data = weather.forecast(**location,at=at)
            except ServiceUnavailable:
                weather_message = 'Прогноз недоступен или город не выбран. Подбор выполнен без погоды; её вес отключён.'
                if options['weather_failure'] == 'abort':
                    return Response({'detail':weather_message,'weather_status':'unavailable'},status=503)
        # Keep selected items stable until all generated outfits have been stored.
        with transaction.atomic():
            items = list(ClothingItem.objects.filter(user=request.user).select_related('category').prefetch_related('colors').order_by('pk').select_for_update(of=('self',))[:501])
            if len(items) > 500:
                raise serializers.ValidationError('Сейчас генератор поддерживает до 500 вещей в гардеробе.')
            pref = OutfitPreference.objects.filter(user=request.user).prefetch_related('preferred_colors','disliked_colors','excluded_categories').first()
            profile = UserProfile.objects.filter(user=request.user).first()
            algorithm_options = dict(options)
            if weather_data:
                algorithm_options['temperature_c'] = max(-60,min(60,weather_data['apparent_temperature_c']))
            results, info = generate(items, algorithm_options, pref, profile, weather_context=weather_data)
            if weather_data:
                context = weather.save_context(request.user,weather_data)
                info['weather'] = {**weather_data,'id':context.pk}
            else:
                info['weather'] = None
            info['weather_status'] = 'ok' if weather_data else ('unavailable' if options['use_weather'] else 'not_requested')
            if weather_message:
                info['messages'].append(weather_message)
            outfits = []
            for index, result in enumerate(results, 1):
                outfit = Outfit.objects.create(user=request.user, name=f"Looksy · {options['occasion']} · {index}", generation={**result['evaluation'], 'request':options, 'messages':info['messages'], 'weather':weather_data, 'algorithm':'rules-v2', 'item_versions':{str(item.pk):item.updated_at.isoformat() for item in result['items']}})
                OutfitItem.objects.bulk_create([OutfitItem(outfit=outfit, clothing_item=item) for item in result['items']])
                outfits.append(outfit.pk)
            saved = Outfit.objects.filter(user=request.user, pk__in=outfits).prefetch_related('items__category','items__photo','items__colors').order_by('pk')
            data = OutfitSerializer(saved, many=True, context={'request':request}).data
        return Response({**info, 'results':data}, status=201 if data else 200)
