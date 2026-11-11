from django.test import TestCase
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient
from .models import User, ClothingCategory, ClothingItem, Outfit, OutfitItem, OutfitFeedback, SavedOutfit, UserProfile, OutfitPreference, WeatherContext
from django.utils import timezone

class APITests(TestCase):
    def setUp(self):
        self.a = User.objects.create_user(username='alice',password='Strong-Test!9981')
        self.b = User.objects.create_user(username='bob',password='Strong-Test!9981')
        self.category = ClothingCategory.objects.create(name='Shirt',slot='top')
        self.own = ClothingItem.objects.create(user=self.a,name='My shirt',category=self.category)
        self.foreign = ClothingItem.objects.create(user=self.b,name='Private shirt',category=self.category)
        self.outfit = Outfit.objects.create(user=self.b,name='Private outfit')
        self.client = APIClient()
        self.client.force_authenticate(self.a)
    def test_anonymous_blocked(self):
        self.client.force_authenticate(None)
        for endpoint in ['clothing','outfits','feedback','saved-outfits','weather','categories','colors']:
            self.assertEqual(self.client.get(f'/api/{endpoint}/').status_code,403)
    def test_clothing_isolation(self):
        data = self.client.get('/api/clothing/').json()['results']
        self.assertEqual([x['id'] for x in data],[self.own.pk])
        url=f'/api/clothing/{self.foreign.pk}/'
        self.assertEqual(self.client.get(url).status_code,404)
        self.assertEqual(self.client.patch(url,{'name':'Hacked'}).status_code,404)
        self.assertEqual(self.client.delete(url).status_code,404)
    def test_owner_cannot_be_spoofed(self):
        response = self.client.post('/api/clothing/',{'name':'New','category':self.category.pk,'user':self.b.pk})
        self.assertEqual(response.status_code,201)
        self.assertEqual(ClothingItem.objects.get(pk=response.data['id']).user,self.a)
    def test_cross_owner_relationships_rejected(self):
        self.assertEqual(self.client.post('/api/outfits/',{'name':'Bad','items':[self.foreign.pk]},format='json').status_code,400)
        for url in ['feedback','saved-outfits']:
            self.assertEqual(self.client.post(f'/api/{url}/',{'outfit':self.outfit.pk,'rating':4}).status_code,400)
    def test_outfit_create_update_and_duplicate(self):
        response=self.client.post('/api/outfits/',{'name':'Daily','items':[self.own.pk]},format='json')
        self.assertEqual(response.status_code,201)
        outfit=Outfit.objects.get(pk=response.data['id'])
        self.assertEqual(list(outfit.items.all()),[self.own])
        url=f'/api/outfits/{outfit.pk}/'
        self.assertEqual(self.client.patch(url,{'items':[self.foreign.pk]},format='json').status_code,400)
        self.assertEqual(list(outfit.items.all()),[self.own])
        self.assertEqual(self.client.patch(url,{'items':[self.own.pk,self.own.pk]},format='json').status_code,400)
    def test_feedback_and_saved_constraints(self):
        outfit=Outfit.objects.create(user=self.a,name='Daily')
        self.assertEqual(self.client.post('/api/feedback/',{'outfit':outfit.pk,'rating':6}).status_code,400)
        for url, data in [('feedback',{'outfit':outfit.pk,'rating':5}),('saved-outfits',{'outfit':outfit.pk})]:
            self.assertEqual(self.client.post(f'/api/{url}/',data).status_code,201)
            self.assertEqual(self.client.post(f'/api/{url}/',data).status_code,400)
    def test_foreign_resources_hidden(self):
        OutfitFeedback.objects.create(user=self.b,outfit=self.outfit,rating=4)
        SavedOutfit.objects.create(user=self.b,outfit=self.outfit)
        WeatherContext.objects.create(user=self.b,latitude=0,longitude=0,temperature_c=20,condition='clear',observed_at=timezone.now())
        for endpoint in ['outfits','feedback','saved-outfits','weather']:
            self.assertEqual(self.client.get(f'/api/{endpoint}/').json()['count'],0)
    def test_database_constraints(self):
        OutfitItem.objects.create(outfit=self.outfit,clothing_item=self.foreign)
        with self.assertRaises(IntegrityError),transaction.atomic():
            OutfitItem.objects.create(outfit=self.outfit,clothing_item=self.foreign)
        with self.assertRaises(IntegrityError),transaction.atomic():
            OutfitFeedback.objects.create(user=self.b,outfit=self.outfit,rating=0)
    def test_delete_account_cascades(self):
        UserProfile.objects.create(user=self.a)
        OutfitPreference.objects.create(user=self.a)
        outfit=Outfit.objects.create(user=self.a,name='Delete me')
        outfit.items.add(self.own)
        self.assertEqual(self.client.delete('/api/account/',{'password':'wrong'},format='json').status_code,400)
        self.assertEqual(self.client.delete('/api/account/',{'password':'Strong-Test!9981'},format='json').status_code,204)
        self.assertFalse(User.objects.filter(pk=self.a.pk).exists())
        self.assertFalse(ClothingItem.objects.filter(pk=self.own.pk).exists())
        self.assertFalse(Outfit.objects.filter(pk=outfit.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.b.pk).exists())
    def test_registration_password_validation(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post('/api/auth/register/',{'username':'new','password':'123'}).status_code,400)
        data={'username':'new','password':'Powerful-New!2991'}
        self.assertEqual(self.client.post('/api/auth/register/',data).status_code,201)
        self.assertTrue(User.objects.get(username='new').check_password(data['password']))
        self.assertTrue(UserProfile.objects.filter(user__username='new').exists())
        self.assertEqual(self.client.post('/api/auth/register/',data).status_code,400)
    def test_real_session_and_csrf(self):
        client=APIClient(enforce_csrf_checks=True)
        data={'username':'alice','password':'Strong-Test!9981'}
        self.assertEqual(client.post('/api/auth/session/',data).status_code,403)
        token=client.get('/api/auth/session/').json()['csrfToken']
        self.assertEqual(client.post('/api/auth/session/',data,HTTP_X_CSRFTOKEN=token).status_code,200)
        self.assertEqual(client.get('/api/account/').status_code,200)
        self.assertEqual(client.post('/api/clothing/',{'name':'X','category':self.category.pk}).status_code,403)
        token=client.get('/api/auth/session/').json()['csrfToken']
        self.assertEqual(client.delete('/api/auth/session/',HTTP_X_CSRFTOKEN=token).status_code,204)
        self.assertEqual(client.get('/api/account/').status_code,403)

class JWTTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(username='jwt_user',password='Secure-Jwt!9012')
        self.client=APIClient()
    def test_token_rotation_and_logout(self):
        response=self.client.post('/api/auth/token/',{'username':'jwt_user','password':'Secure-Jwt!9012'})
        self.assertEqual(response.status_code,200)
        tokens=response.json()
        self.client.credentials(HTTP_AUTHORIZATION='Bearer '+tokens['access'])
        self.assertEqual(self.client.get('/api/account/').status_code,200)
        response=self.client.post('/api/auth/token/refresh/',{'refresh':tokens['refresh']})
        self.assertEqual(response.status_code,200)
        new=response.json()
        self.assertEqual(self.client.post('/api/auth/token/refresh/',{'refresh':tokens['refresh']}).status_code,401)
        self.assertEqual(self.client.post('/api/auth/token/logout/',{'refresh':new['refresh']}).status_code,200)
        self.assertEqual(self.client.post('/api/auth/token/refresh/',{'refresh':new['refresh']}).status_code,401)
    def test_invalid_credentials_and_access(self):
        self.assertEqual(self.client.post('/api/auth/token/',{'username':'jwt_user','password':'wrong'}).status_code,401)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid')
        self.assertIn(self.client.get('/api/account/').status_code,[401,403])
    def test_deleted_account_token_invalid(self):
        tokens=self.client.post('/api/auth/token/',{'username':'jwt_user','password':'Secure-Jwt!9012'}).json()
        self.client.credentials(HTTP_AUTHORIZATION='Bearer '+tokens['access'])
        self.assertEqual(self.client.delete('/api/account/',{'password':'Secure-Jwt!9012'},format='json').status_code,204)
        self.assertIn(self.client.get('/api/account/').status_code,[401,403])
        self.assertEqual(self.client.post('/api/auth/token/refresh/',{'refresh':tokens['refresh']}).status_code,401)
    def test_admin_requires_staff(self):
        response=self.client.get('/admin/')
        self.assertEqual(response.status_code,302)
        self.assertIn('/admin/login/',response.url)
