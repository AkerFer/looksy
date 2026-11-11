from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import ClothingItem, OutfitPreference, UserProfile, WeatherContext
from .serializers import ClothingItemSerializer
from .generator import generate
from .generation_api import GenerationSerializer
from .services.stylist import advise
from .services.http import ServiceUnavailable


class StylistRequestSerializer(serializers.Serializer):
    message=serializers.CharField(max_length=1000)
    use_ai=serializers.BooleanField(default=True)
    weather_context_id=serializers.IntegerField(min_value=1, required=False)


class StylistView(APIView):
    def post(self,request):
        serializer=StylistRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        options=serializer.validated_data
        weather_snapshot=None
        if 'weather_context_id' in options:
            from django.shortcuts import get_object_or_404
            from .serializers import WeatherSerializer
            context=get_object_or_404(WeatherContext,user=request.user,pk=options['weather_context_id'])
            weather_snapshot=dict(WeatherSerializer(context).data)
        items=list(ClothingItem.objects.filter(user=request.user,is_available=True).select_related('category','photo').prefetch_related('colors').order_by('pk')[:501])
        if len(items)>500:
            raise serializers.ValidationError('Стилист поддерживает до 500 доступных вещей.')
        preference=OutfitPreference.objects.filter(user=request.user).prefetch_related('preferred_colors','disliked_colors','excluded_categories').first()
        profile=UserProfile.objects.filter(user=request.user).first()
        excluded={c.pk for c in preference.excluded_categories.all()} if preference else set()
        items=[item for item in items if item.category_id not in excluded]
        if options['use_ai']:
            try:
                prefs={'styles':preference.styles if preference else [],'preferred_fit':preference.preferred_fit if preference else 'unknown','comfort_priority':preference.comfort_priority if preference else 50,'preferred_colors':[c.hex_code for c in preference.preferred_colors.all()] if preference else [],'disliked_colors':[c.hex_code for c in preference.disliked_colors.all()] if preference else []}
                prefs['weather_snapshot']=weather_snapshot
                answer=advise(options['message'],items,prefs)
                selected=[item for item in items if item.pk in answer['item_ids']]
                return Response({**answer,'source':'ollama','weather_snapshot':weather_snapshot,'items':ClothingItemSerializer(selected,many=True).data,'warnings':['Совет модели может ошибаться. Карточки вещей проверены по вашему гардеробу; текст — рекомендация, а не факт об инвентаре.']+([f'Для AI переданы первые {answer["context_count"]} доступных вещей из-за лимита контекста.'] if len(items)>answer['context_count'] else [])})
            except ServiceUnavailable:
                pass
        defaults=GenerationSerializer(data={}); defaults.is_valid(raise_exception=True)
        fallback_options=dict(defaults.validated_data)
        if weather_snapshot and weather_snapshot['apparent_temperature_c'] is not None:
            fallback_options['temperature_c']=max(-60,min(60,weather_snapshot['apparent_temperature_c']))
        results,info=generate(items,fallback_options,preference,profile,weather_context=weather_snapshot if weather_snapshot and weather_snapshot['apparent_temperature_c'] is not None and weather_snapshot['precipitation_probability'] is not None and weather_snapshot['wind_speed_kmh'] is not None else None)
        selected=results[0]['items'] if results else []
        slots={item.category.slot for item in items}
        missing=[]
        if 'shoes' not in slots: missing.append('shoes')
        if 'dress' not in slots:
            if 'top' not in slots: missing.append('top')
            if 'bottom' not in slots: missing.append('bottom')
        return Response({'source':'rules','message':'AI-модель недоступна или отключена. Предлагаю базовый комплект из доступных вещей.' if selected else 'AI-модель недоступна или отключена. Для полного комплекта не хватает совместимых вещей.',
                         'item_ids':[item.pk for item in selected], 'items':ClothingItemSerializer(selected,many=True).data,
                         'weather_snapshot':weather_snapshot,'missing_slots':missing,'warnings':['Резервный алгоритм не понимает свободный текст; используйте параметры генератора.','Недостающие категории — предложения, они не добавляются в гардероб.'], 'outfits':[[item.pk for item in result['items']] for result in results]})
