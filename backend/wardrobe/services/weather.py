from datetime import datetime, timedelta, timezone as dtz
import math
from django.core.cache import cache
from django.utils import timezone
from .http import json_request, ServiceUnavailable


def number(value, minimum, maximum):
    if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError('Invalid number')
    return value


def locations(search):
    data=json_request('GET','https://geocoding-api.open-meteo.com/v1/search',params={'name':search,'count':5,'language':'ru','format':'json'},retries=1)
    try:
        rows=data.get('results',[])
        if not isinstance(rows,list): raise ValueError()
        return [{'id':int(row['id']),'name':str(row['name'])[:150],'country':str(row.get('country',''))[:100],
                 'region':str(row.get('admin1',''))[:100], 'latitude':number(row['latitude'],-90,90),
                 'longitude':number(row['longitude'],-180,180),'timezone':str(row.get('timezone','UTC'))[:80]} for row in rows[:5]]
    except (KeyError,TypeError,ValueError):
        raise ServiceUnavailable('Некорректный ответ поиска городов.') from None


def forecast(latitude, longitude, at=None):
    now=timezone.now()
    at=at or now
    if not timezone.is_aware(at) or not now-timedelta(hours=1) <= at <= now+timedelta(days=6):
        raise ValueError('Выберите время от текущего часа до шести дней вперёд, с часовым поясом.')
    day=at.astimezone(dtz.utc).date().isoformat()
    key=f'forecast:v1:{float(latitude):.5f}:{float(longitude):.5f}:{day}'
    data=cache.get(key)
    cached=data is not None
    if data is None:
        response=json_request('GET','https://api.open-meteo.com/v1/forecast',params={'latitude':float(latitude),'longitude':float(longitude),'hourly':'temperature_2m,apparent_temperature,precipitation_probability,wind_speed_10m,weather_code','timezone':'UTC','start_date':day,'end_date':day,'wind_speed_unit':'kmh'},retries=1)
        try:
            hourly=response['hourly']
            fields=['time','temperature_2m','apparent_temperature','precipitation_probability','wind_speed_10m','weather_code']
            if not all(isinstance(hourly[k],list) for k in fields) or not 1 <= len(hourly['time']) <= 48 or any(len(hourly[k])!=len(hourly['time']) for k in fields):
                raise ValueError()
            rows=[]
            for i, stamp in enumerate(hourly['time']):
                valid=datetime.fromisoformat(stamp).replace(tzinfo=dtz.utc)
                rain=number(hourly['precipitation_probability'][i],0,100)
                if rain != int(rain): raise ValueError()
                rows.append({'forecast_for':valid.isoformat(),'temperature_c':number(hourly['temperature_2m'][i],-100,70),'apparent_temperature_c':number(hourly['apparent_temperature'][i],-100,70),'precipitation_probability':int(rain),'wind_speed_kmh':number(hourly['wind_speed_10m'][i],0,500),'condition':str(int(number(hourly['weather_code'][i],0,99)))})
            data={'rows':rows,'fetched_at':now.isoformat()}
            cache.set(key,data,600)
        except (KeyError,ValueError,TypeError,OverflowError):
            raise ServiceUnavailable('Погодный сервис вернул некорректный прогноз.') from None
    row=min(data['rows'],key=lambda r:abs(datetime.fromisoformat(r['forecast_for'])-at))
    if abs(datetime.fromisoformat(row['forecast_for'])-at) > timedelta(hours=1):
        raise ServiceUnavailable('Нет прогноза на выбранный час.')
    return {**row,'latitude':float(latitude),'longitude':float(longitude),'source':'open-meteo','observed_at':data['fetched_at'],'cached':cached}


def save_context(user, data):
    from ..models import WeatherContext
    fields={key:data[key] for key in ['latitude','longitude','temperature_c','apparent_temperature_c','precipitation_probability','wind_speed_kmh','condition','forecast_for','observed_at','source']}
    return WeatherContext.objects.create(user=user,**fields)
