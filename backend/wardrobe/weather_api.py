from datetime import datetime
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from .services import weather
from .services.http import ServiceUnavailable


class AwareDateTimeField(serializers.DateTimeField):
    def to_internal_value(self, value):
        try:
            stamp=datetime.fromisoformat(value.replace('Z','+00:00')) if isinstance(value,str) else value
            if not isinstance(stamp,datetime) or not timezone.is_aware(stamp): raise ValueError()
        except (ValueError,TypeError):
            raise serializers.ValidationError('Укажите дату ISO 8601 с часовым поясом.') from None
        return super().to_internal_value(value)


class CoordinatesSerializer(serializers.Serializer):
    latitude=serializers.DecimalField(max_digits=8,decimal_places=5,min_value=-90,max_value=90)
    longitude=serializers.DecimalField(max_digits=8,decimal_places=5,min_value=-180,max_value=180)


class ForecastSerializer(CoordinatesSerializer):
    at=AwareDateTimeField(required=False)

    def validate(self, attrs):
        from datetime import timedelta
        if 'at' in attrs and not timezone.now()-timedelta(hours=1) <= attrs['at'] <= timezone.now()+timedelta(days=6):
            raise serializers.ValidationError({'at':'Прогноз доступен от текущего часа до шести дней вперёд.'})
        return attrs


class LocationsView(APIView):
    def get(self,request):
        field=serializers.CharField(min_length=2,max_length=150)
        search=field.run_validation(request.query_params.get('search'))
        try:
            return Response({'results':weather.locations(search),'source':'open-meteo'})
        except ServiceUnavailable:
            return Response({'detail':'Поиск городов временно недоступен. Можно указать координаты вручную.'},status=503)


class ForecastView(APIView):
    def post(self,request):
        serializer=ForecastSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            data=weather.forecast(**serializer.validated_data)
        except ServiceUnavailable:
            return Response({'detail':'Погода временно недоступна. Укажите температуру вручную или продолжите без погоды.'},status=503)
        except ValueError as exc:
            raise serializers.ValidationError({'at':str(exc)}) from None
        context=weather.save_context(request.user,data)
        return Response({**data,'id':context.pk})
