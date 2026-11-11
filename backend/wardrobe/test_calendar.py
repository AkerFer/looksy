from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from .models import User, Outfit, OutfitCalendarEntry

class CalendarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user=User.objects.create_user(username='calendar-owner',password='Calendar-Safe!8812')
        cls.other=User.objects.create_user(username='calendar-other')
        cls.own=Outfit.objects.create(user=cls.user,name='Mine')
        cls.foreign=Outfit.objects.create(user=cls.other,name='Private')
    def setUp(self):
        self.client=APIClient(); self.client.force_authenticate(self.user)
    def test_calendar_crud_and_unique_date(self):
        data={'date':'2026-12-01','outfit':self.own.pk,'note':'Meeting'}
        response=self.client.post('/api/calendar/',data,format='json')
        self.assertEqual(response.status_code,201)
        self.assertEqual(response.data['outfit_details']['name'],'Mine')
        url=f"/api/calendar/{response.data['id']}/"
        self.assertEqual(self.client.post('/api/calendar/',data,format='json').status_code,400)
        self.assertEqual(self.client.patch(url,{'note':'Edited'},format='json').status_code,200)
        self.assertEqual(self.client.delete(url).status_code,204)
        self.assertFalse(OutfitCalendarEntry.objects.exists())
    def test_calendar_owner_and_relations_isolated(self):
        foreign=OutfitCalendarEntry.objects.create(user=self.other,outfit=self.foreign,date='2026-12-01')
        self.assertEqual(self.client.get('/api/calendar/').data['count'],0)
        self.assertEqual(self.client.post('/api/calendar/',{'date':'2026-12-01','outfit':self.foreign.pk}).status_code,400)
        url=f'/api/calendar/{foreign.pk}/'
        self.assertEqual(self.client.get(url).status_code,404)
        self.assertEqual(self.client.patch(url,{'note':'Hacked'}).status_code,404)
        self.assertEqual(self.client.delete(url).status_code,404)
        self.assertEqual(self.client.post('/api/calendar/',{'date':'2026-12-01','outfit':self.own.pk}).status_code,201)
    def test_validation_and_cascade(self):
        self.assertEqual(self.client.post('/api/calendar/',{'date':'invalid','outfit':self.own.pk}).status_code,400)
        record=OutfitCalendarEntry.objects.create(user=self.user,outfit=self.own,date='2026-12-01')
        self.user.delete()
        self.assertFalse(OutfitCalendarEntry.objects.filter(pk=record.pk).exists())
    def test_anonymous_calendar_denied(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/calendar/').status_code,403)

    @override_settings(CSRF_TRUSTED_ORIGINS=['http://localhost:3000'])
    def test_frontend_origin_and_csrf_required(self):
        client=APIClient(enforce_csrf_checks=True)
        token=client.get('/api/auth/session/').data['csrfToken']
        credentials={'username':'calendar-owner','password':'Calendar-Safe!8812'}
        self.assertEqual(client.post('/api/auth/session/',credentials,HTTP_ORIGIN='http://localhost:3000',HTTP_X_CSRFTOKEN=token).status_code,200)
        self.assertEqual(client.post('/api/calendar/',{'date':'2026-12-01','outfit':self.own.pk},HTTP_ORIGIN='http://localhost:3000').status_code,403)
        token=client.get('/api/auth/session/').data['csrfToken']
        self.assertEqual(client.post('/api/calendar/',{'date':'2026-12-01','outfit':self.own.pk},HTTP_ORIGIN='http://localhost:3000',HTTP_X_CSRFTOKEN=token).status_code,201)
        self.assertEqual(client.post('/api/calendar/',{'date':'2026-12-02','outfit':self.own.pk},HTTP_ORIGIN='http://attacker.invalid',HTTP_X_CSRFTOKEN=token).status_code,403)
