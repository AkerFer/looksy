from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient
from .models import (User, UserProfile, OutfitPreference, ClothingItem,
                     ClothingCategory, ClothingColor, Outfit)


class WardrobeWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='wardrobe-owner', password='Safe-Pass!9021')
        cls.other = User.objects.create_user(username='other-owner', password='Safe-Pass!9021')
        cls.top = ClothingCategory.objects.create(name='Test tops', slot='top')
        cls.bottom = ClothingCategory.objects.create(name='Test bottoms', slot='bottom')
        cls.red = ClothingColor.objects.create(name='Test red', hex_code='#FF0022')
        cls.blue = ClothingColor.objects.create(name='Test blue', hex_code='#000022')
        cls.shirt = ClothingItem.objects.create(user=cls.user, name='Red shirt', category=cls.top, season='summer', brand='Looksy', fit='regular')
        cls.shirt.colors.add(cls.red, cls.blue)
        cls.jeans = ClothingItem.objects.create(user=cls.user, name='Blue jeans', category=cls.bottom, is_available=False, description='Favourite denim')
        cls.jeans.colors.add(cls.blue)
        cls.foreign = ClothingItem.objects.create(user=cls.other, name='Secret shirt', category=cls.top, season='summer')
        cls.foreign.colors.add(cls.red)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_combined_filters_and_search(self):
        response = self.client.get('/api/clothing/', {'search':'shirt', 'category':self.top.pk, 'color':self.red.pk, 'season':'summer', 'is_available':'true', 'slot':'top', 'fit':'regular'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([x['id'] for x in response.data['results']], [self.shirt.pk])
        for term in ['looksy', 'RED']:
            self.assertEqual(self.client.get('/api/clothing/', {'search':term}).data['count'], 1)
        self.assertEqual(self.client.get('/api/clothing/', {'search':'denim'}).data['results'][0]['id'], self.jeans.pk)
        self.assertEqual(self.client.get('/api/clothing/', {'is_available':'false'}).data['results'][0]['id'], self.jeans.pk)
        self.assertEqual(self.client.get('/api/clothing/', {'search':'Secret'}).data['count'], 0)

    def test_bad_filters_are_errors(self):
        for params in [{'category':'oops'}, {'category':0}, {'is_available':'maybe'}, {'season':'moon'}, {'fit':'invented'}, {'ordering':'user__password'}, {'typo':'summer'}, {'color':'-1'}, {'slot':'bad'}]:
            with self.subTest(params=params):
                self.assertEqual(self.client.get('/api/clothing/', params).status_code, 400)
        self.assertEqual(self.client.get('/api/clothing/?color=1&color=2').status_code, 400)

    def test_summary_is_scoped_and_filtered(self):
        response = self.client.get('/api/clothing/summary/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total'], 2)
        self.assertEqual(response.data['available'], 1)
        self.assertEqual(response.data['unavailable'], 1)
        self.assertEqual(sum(row['count'] for row in response.data['categories']), 2)
        self.assertEqual(self.client.get('/api/clothing/summary/', {'color':self.red.pk}).data['total'], 1)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/clothing/summary/').data['total'], 1)

    def test_ordering_and_pagination_have_no_duplicates(self):
        ClothingItem.objects.bulk_create([ClothingItem(user=self.user, name='Same name', category=self.top) for _ in range(33)])
        response = self.client.get('/api/clothing/', {'ordering':'name'})
        self.assertEqual(response.data['count'], 35)
        first = [x['id'] for x in response.data['results']]
        second = [x['id'] for x in self.client.get(response.data['next']).data['results']]
        self.assertEqual(len(first + second), len(set(first + second)))
        self.assertNotIn(self.foreign.pk, first + second)

    def test_clothing_edit_validation_and_delete(self):
        response = self.client.post('/api/clothing/', {'name':'New jacket', 'category':self.top.pk, 'colors':[self.red.pk], 'brand':'Local', 'material':'Cotton', 'styles':['Casual'], 'fit':'relaxed'}, format='json')
        self.assertEqual(response.status_code, 201)
        item_id = response.data['id']
        url = f'/api/clothing/{item_id}/'
        response = self.client.patch(url, {'name':'Edited', 'is_available':False, 'colors':[self.blue.pk]}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['is_available'])
        self.assertEqual(response.data['colors'], [self.blue.pk])
        self.assertEqual(response.data['material'], 'Cotton')
        for payload in [{'styles':'casual'}, {'styles':['a', 'A']}, {'styles':['']}, {'fit':'made-up'}, {'category':999999}, {'colors':[999999]}, {'name':''}]:
            self.assertEqual(self.client.patch(url, payload, format='json').status_code, 400)
        outfit = Outfit.objects.create(user=self.user, name='Saved composition')
        outfit.items.add(item_id)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(outfit.items.exists())
        self.assertTrue(ClothingItem.objects.filter(pk=self.foreign.pk).exists())

    def test_profile_persistence_and_isolation(self):
        response = self.client.patch('/api/profile/', {'display_name':'Анна', 'city':'Ташкент', 'cold_sensitivity':5, 'heat_sensitivity':1}, format='json')
        self.assertEqual(response.status_code, 200)
        profile = self.client.get('/api/profile/').data
        self.assertEqual(profile['city'], 'Ташкент')
        self.assertEqual(profile['cold_sensitivity'], 5)
        self.client.force_authenticate(self.other)
        other = self.client.get('/api/profile/').data
        self.assertEqual(other['city'], '')
        self.assertNotEqual(other['id'], profile['id'])
        self.assertEqual(self.client.patch('/api/profile/', {'cold_sensitivity':0}, format='json').status_code, 400)
        self.assertEqual(self.client.patch('/api/profile/', {'heat_sensitivity':6}, format='json').status_code, 400)

    def test_preferences_partial_update_validation_and_clear(self):
        data = {'styles':['Minimalism', 'Casual'], 'preferred_colors':[self.red.pk], 'disliked_colors':[self.blue.pk], 'preferred_fit':'oversized', 'comfort_priority':80, 'excluded_categories':[self.bottom.pk]}
        response = self.client.patch('/api/preferences/', data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/preferences/').data['styles'], data['styles'])
        self.assertEqual(self.client.patch('/api/preferences/', {'preferred_colors':[self.blue.pk]}, format='json').status_code, 400)
        self.assertEqual(self.client.get('/api/preferences/').data['preferred_colors'], [self.red.pk])
        for payload in [{'comfort_priority':101}, {'comfort_priority':-1}, {'styles':list(map(str,range(21)))}, {'preferred_colors':[999999]}, {'excluded_categories':[999999]}]:
            self.assertEqual(self.client.patch('/api/preferences/', payload, format='json').status_code, 400)
        self.assertEqual(self.client.patch('/api/preferences/', {'preferred_colors':[], 'disliked_colors':[], 'styles':[]}, format='json').status_code, 200)
        self.client.force_authenticate(self.other)
        other = self.client.get('/api/preferences/').data
        self.assertEqual(other['comfort_priority'], 50)
        self.assertEqual(other['preferred_colors'], [])

    def test_anonymous_profile_and_filters_blocked(self):
        self.client.force_authenticate(None)
        for url in ['/api/profile/', '/api/preferences/', '/api/clothing/summary/', '/api/clothing/?search=shirt']:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_registration_name_csrf_and_password_secrecy(self):
        client = APIClient(enforce_csrf_checks=True)
        payload = {'username':'new-owner', 'password':'Secure-Registration!782', 'display_name':'Маша', 'email':'masha@example.com'}
        self.assertEqual(client.post('/api/auth/register/', payload).status_code, 403)
        csrf = client.get('/api/auth/session/').data['csrfToken']
        response = client.post('/api/auth/register/', payload, HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('password', response.data)
        user = User.objects.get(username=payload['username'])
        self.assertEqual(user.profile.display_name, 'Маша')
        self.assertTrue(user.check_password(payload['password']))
        self.assertTrue(OutfitPreference.objects.filter(user=user).exists())
        self.assertEqual(client.post('/api/auth/register/', payload, HTTP_X_CSRFTOKEN=csrf).status_code, 400)

    def test_database_limits(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            UserProfile.objects.create(user=self.user, cold_sensitivity=6)
        with self.assertRaises(IntegrityError), transaction.atomic():
            OutfitPreference.objects.create(user=self.user, comfort_priority=101)

    def test_filtered_foreign_resource_still_inaccessible(self):
        url = f'/api/clothing/{self.foreign.pk}/?search=Secret'
        self.assertEqual(self.client.patch(url, {'name':'Steal'}, format='json').status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)
