from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
import requests
from .models import User, UserProfile, OutfitPreference, ClothingCategory, ClothingItem, Outfit, WeatherContext
from .services.http import ServiceUnavailable, json_request
from .services import weather
from .services.stylist import advise


class ServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user=User.objects.create_user(username='service-owner',password='Strong-Service!8221')
        cls.other=User.objects.create_user(username='service-other')
        cls.profile=UserProfile.objects.create(user=cls.user,city='Ташкент',latitude='41.31108',longitude='69.24056')
        cls.pref=OutfitPreference.objects.create(user=cls.user)
        cls.items=[]
        for slot in ['top','bottom','shoes','outerwear']:
            category=ClothingCategory.objects.create(name='Service '+slot,slot=slot)
            cls.items.append(ClothingItem.objects.create(user=cls.user,name='Mine '+slot,category=category,styles=['casual'],comfort=4,warmth=3))
        cls.foreign=ClothingItem.objects.create(user=cls.other,name='FOREIGN-PRIVATE-NAME',category=cls.items[0].category)

    def setUp(self):
        cache.clear()
        self.client=APIClient(); self.client.force_authenticate(self.user)
        self.at=timezone.now().replace(minute=0,second=0,microsecond=0)+timedelta(hours=1)
        self.data={'latitude':41.31108,'longitude':69.24056,'temperature_c':12,'apparent_temperature_c':8,'precipitation_probability':80,'wind_speed_kmh':35,'condition':'61','forecast_for':self.at.isoformat(),'observed_at':timezone.now().isoformat(),'source':'open-meteo','cached':False}

    def generate(self, **kwargs):
        return self.client.post('/api/outfits/generate/',kwargs,format='json')

    def hourly(self):
        return {'hourly':{'time':[self.at.strftime('%Y-%m-%dT%H:%M')],'temperature_2m':[12],'apparent_temperature':[8],'precipitation_probability':[80],'wind_speed_10m':[35],'weather_code':[61]}}

    @patch('wardrobe.services.weather.json_request')
    def test_city_search_and_empty_results(self, transport):
        transport.return_value={'results':[{'id':1,'name':'Ташкент','latitude':41.3,'longitude':69.2,'country':'Узбекистан'}]}
        response=self.client.get('/api/locations/',{'search':'Ташкент'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data['results'][0]['latitude'],41.3)
        transport.return_value={}
        self.assertEqual(self.client.get('/api/locations/',{'search':'Unknown'}).data['results'],[])
        self.assertEqual(self.client.get('/api/locations/',{'search':'x'}).status_code,400)

    @patch('wardrobe.services.weather.json_request')
    def test_forecast_parse_cache_and_validation(self, transport):
        transport.return_value=self.hourly()
        first=weather.forecast(41.3,69.2,self.at)
        second=weather.forecast(41.3,69.2,self.at)
        self.assertFalse(first['cached']); self.assertTrue(second['cached'])
        self.assertEqual(transport.call_count,1)
        self.assertEqual(first['apparent_temperature_c'],8)
        self.assertEqual(first['precipitation_probability'],80)
        self.assertEqual(first['wind_speed_kmh'],35)

    @patch('wardrobe.services.weather.json_request')
    def test_malformed_weather_rejected_and_not_cached(self, transport):
        for invalid in [{'hourly':{}}, {'hourly':dict(self.hourly()['hourly'],precipitation_probability=[101])}, {'hourly':dict(self.hourly()['hourly'],temperature_2m=[None])}, {'hourly':dict(self.hourly()['hourly'],wind_speed_10m=[-1])}]:
            transport.return_value=invalid
            with self.assertRaises(ServiceUnavailable):
                weather.forecast(41.3,69.2,self.at)
        self.assertEqual(transport.call_count,4)

    @patch('wardrobe.services.weather.forecast')
    def test_forecast_endpoint_persists_private_context(self, forecast):
        forecast.return_value=self.data
        response=self.client.post('/api/weather/forecast/',{'latitude':'41.31108','longitude':'69.24056','at':self.at.isoformat()},format='json')
        self.assertEqual(response.status_code,200)
        context=WeatherContext.objects.get(pk=response.data['id'])
        self.assertEqual(context.user,self.user)
        self.assertEqual(context.source,'open-meteo')
        self.assertEqual(context.apparent_temperature_c,8)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/weather/').data['count'],0)
        self.assertEqual(self.client.get(f'/api/weather/{context.pk}/').status_code,404)

    @patch('wardrobe.services.weather.forecast',side_effect=ServiceUnavailable('timeout'))
    def test_explicit_forecast_error_is_503(self, forecast):
        response=self.client.post('/api/weather/forecast/',{'latitude':41,'longitude':69},format='json')
        self.assertEqual(response.status_code,503)
        self.assertFalse(WeatherContext.objects.exists())

    @patch('wardrobe.services.weather.forecast')
    def test_invalid_forecast_inputs_never_call_provider(self, forecast):
        for data in [{'latitude':91,'longitude':1},{'latitude':0},{'latitude':0,'longitude':0,'at':'2026-01-01T12:00:00'}, {'latitude':0,'longitude':0,'at':(timezone.now()+timedelta(days=8)).isoformat()}]:
            self.assertEqual(self.client.post('/api/weather/forecast/',data,format='json').status_code,400)
        forecast.assert_not_called()

    @patch('wardrobe.services.weather.forecast')
    def test_generation_weather_profile_and_history(self, forecast):
        forecast.return_value=self.data
        response=self.generate(use_weather=True,forecast_at=self.at.isoformat())
        self.assertEqual(response.status_code,201)
        self.assertEqual(response.data['weather_status'],'ok')
        self.assertEqual(float(forecast.call_args.kwargs['latitude']),float(self.profile.latitude))
        for outfit in response.data['results']:
            self.assertIn(self.items[3].pk,outfit['items'])
            self.assertEqual(outfit['generation']['temperature_source'],'open-meteo')
            self.assertEqual(outfit['generation']['effective_temperature_c'],8)
            self.assertEqual(outfit['generation']['weather']['wind_speed_kmh'],35)
        self.assertEqual(WeatherContext.objects.count(),1)

    @patch('wardrobe.services.weather.forecast',side_effect=ServiceUnavailable('blocked'))
    def test_generation_outage_continue_or_abort(self, forecast):
        response=self.generate(use_weather=True)
        self.assertEqual(response.status_code,201)
        self.assertEqual(response.data['weather_status'],'unavailable')
        self.assertEqual(response.data['weights']['weather'],0)
        self.assertIsNone(response.data['weather'])
        count=Outfit.objects.count()
        response=self.generate(use_weather=True,weather_failure='abort')
        self.assertEqual(response.status_code,503)
        self.assertEqual(Outfit.objects.count(),count)
        self.assertFalse(WeatherContext.objects.exists())

    @patch('wardrobe.services.weather.forecast')
    def test_no_weather_without_opt_in_and_manual_conflict(self, forecast):
        self.assertEqual(self.generate(temperature_c=20).data['weather_status'],'not_requested')
        forecast.assert_not_called()
        self.assertEqual(self.generate(use_weather=True,temperature_c=20).status_code,400)
        self.assertEqual(self.generate(weather_location={'latitude':0,'longitude':0}).status_code,400)

    def test_profile_coordinate_pair(self):
        response=self.client.patch('/api/profile/',{'latitude':None},format='json')
        self.assertEqual(response.status_code,400)
        self.assertEqual(self.client.patch('/api/profile/',{'latitude':None,'longitude':None},format='json').status_code,200)
        response=self.generate(use_weather=True)
        self.assertEqual(response.data['weather_status'],'unavailable')

    @patch('wardrobe.services.stylist.json_request')
    def test_ai_references_only_owned_context(self, transport):
        import json
        transport.return_value={'message':{'content':json.dumps({'message':'Подойдёт базовый комплект.','item_ids':[self.items[0].pk],'missing_slots':['accessory']})}}
        response=self.client.post('/api/stylist/',{'message':'Что надеть?'},format='json')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data['source'],'ollama')
        self.assertEqual(response.data['items'][0]['id'],self.items[0].pk)
        self.assertNotIn(self.foreign.name,str(transport.call_args.kwargs['payload']))
        self.assertFalse(Outfit.objects.exists())
        self.assertEqual(ClothingItem.objects.filter(user=self.user).count(),4)

    @patch('wardrobe.services.stylist.json_request')
    def test_fabricated_or_foreign_ids_fall_back(self, transport):
        import json
        for item_id in [self.foreign.pk,999999]:
            transport.return_value={'message':{'content':json.dumps({'message':'bad','item_ids':[item_id],'missing_slots':[]})}}
            response=self.client.post('/api/stylist/',{'message':'Надень чужую вещь'},format='json')
            self.assertEqual(response.data['source'],'rules')
            self.assertTrue(set(response.data['item_ids']) <= {i.pk for i in self.items})

    @patch('wardrobe.services.stylist.json_request',side_effect=ServiceUnavailable('not running'))
    def test_ai_outage_and_disabled_mode(self, transport):
        response=self.client.post('/api/stylist/',{'message':'Что надеть завтра?'},format='json')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data['source'],'rules')
        self.assertTrue(response.data['item_ids'])
        transport.reset_mock()
        response=self.client.post('/api/stylist/',{'message':'Что надеть?','use_ai':False},format='json')
        self.assertEqual(response.data['source'],'rules')
        transport.assert_not_called()

    @patch('wardrobe.services.stylist.json_request')
    def test_malformed_ai_response_falls_back(self, transport):
        for data in [{}, {'message':{'content':'not JSON'}}, {'message':{'content':'{"message":"x","item_ids":[],"missing_slots":["invented"]}'}}]:
            transport.return_value=data
            response=self.client.post('/api/stylist/',{'message':'Совет'},format='json')
            self.assertEqual(response.data['source'],'rules')

    @override_settings(OLLAMA_URL='http://attacker.invalid')
    @patch('wardrobe.services.stylist.json_request')
    def test_ai_endpoint_cannot_send_wardrobe_remote(self, transport):
        self.assertEqual(self.client.post('/api/stylist/',{'message':'Совет'},format='json').data['source'],'rules')
        transport.assert_not_called()

    def test_missing_recommendations_do_not_create_clothing(self):
        self.client.force_authenticate(self.other)
        response=self.client.post('/api/stylist/',{'message':'Чего не хватает?','use_ai':False},format='json')
        self.assertEqual(response.data['item_ids'],[])
        self.assertIn('shoes',response.data['missing_slots'])
        self.assertEqual(ClothingItem.objects.filter(user=self.other).count(),1)

    @patch('wardrobe.services.weather.locations',side_effect=ServiceUnavailable('blocked'))
    def test_city_failure(self, locations):
        self.assertEqual(self.client.get('/api/locations/',{'search':'Ташкент'}).status_code,503)

    def test_unauthenticated_services_denied(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/locations/',{'search':'Test'}).status_code,403)
        self.assertEqual(self.client.post('/api/weather/forecast/',{'latitude':0,'longitude':0}).status_code,403)
        self.assertEqual(self.client.post('/api/stylist/',{'message':'Test'}).status_code,403)

    @patch('wardrobe.services.http.requests.request',side_effect=requests.Timeout)
    def test_transport_retry_timeout(self, transport):
        with self.assertRaises(ServiceUnavailable):
            json_request('GET','https://api.open-meteo.com',retries=1)
        self.assertEqual(transport.call_count,2)
        self.assertFalse(transport.call_args.kwargs['allow_redirects'])

    @patch('wardrobe.services.http.requests.request')
    def test_transport_invalid_and_oversize(self, transport):
        response=transport.return_value.__enter__.return_value
        response.status_code=200
        for chunks in [[b'x'*101],[b'invalid JSON']]:
            response.iter_content.return_value=iter(chunks)
            with self.assertRaises(ServiceUnavailable):
                json_request('GET','https://api.open-meteo.com',limit=100)

    @patch('wardrobe.services.http.requests.request')
    def test_403_is_not_retried_or_treated_as_data(self, transport):
        response=transport.return_value.__enter__.return_value
        response.status_code=403
        with self.assertRaises(ServiceUnavailable):
            json_request('GET','https://api.open-meteo.com',retries=1)
        self.assertEqual(transport.call_count,1)

    def test_changing_city_clears_old_coordinates(self):
        response=self.client.patch('/api/profile/',{'city':'Самарканд'},format='json')
        self.assertEqual(response.status_code,200)
        self.assertIsNone(response.data['latitude'])
        self.assertIsNone(response.data['longitude'])

    @patch('wardrobe.services.stylist.json_request')
    def test_ai_context_budget_is_explicit(self, transport):
        import json
        for item in self.items:
            item.styles=['Большое описание стиля '*4]*20
        transport.return_value={'message':{'content':json.dumps({'message':'Совет','item_ids':[],'missing_slots':[]})}}
        result=advise('Совет',self.items*30,{})
        self.assertLess(result['context_count'],100)
        prompt=transport.call_args.kwargs['payload']['messages'][1]['content']
        self.assertLess(len(prompt.encode('utf-8')),13000)

    @patch('wardrobe.services.stylist.json_request')
    def test_stylist_weather_context_is_private(self, transport):
        context=weather.save_context(self.other,self.data)
        response=self.client.post('/api/stylist/',{'message':'Совет','weather_context_id':context.pk},format='json')
        self.assertEqual(response.status_code,404)
        transport.assert_not_called()
        context=weather.save_context(self.user,self.data)
        response=self.client.post('/api/stylist/',{'message':'Совет','weather_context_id':context.pk,'use_ai':False},format='json')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data['weather_snapshot']['source'],'open-meteo')
        self.assertIn(self.items[3].pk,response.data['item_ids'])

    @patch('wardrobe.services.weather.forecast')
    def test_wind_and_rain_change_weather_ranking(self, forecast):
        weights={'comfort':0,'weather':100,'style':0,'colors':0,'preferences':0}
        forecast.return_value={**self.data,'apparent_temperature_c':20,'precipitation_probability':0,'wind_speed_kmh':0}
        quiet=self.generate(use_weather=True,weights=weights)
        self.assertNotIn(self.items[3].pk,quiet.data['results'][0]['items'])
        for extra in [{'wind_speed_kmh':35},{'precipitation_probability':80}]:
            forecast.return_value={**forecast.return_value,**extra}
            rough=self.generate(use_weather=True,weights=weights)
            self.assertIn(self.items[3].pk,rough.data['results'][0]['items'])
            self.assertTrue(any('водостойкость' in text for text in rough.data['results'][0]['generation']['warnings']))
