from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient
from .models import (User, UserProfile, ClothingCategory, ClothingColor,
                     ClothingItem, Outfit, OutfitPreference, SavedOutfit)
from .generator import color_pair


class GeneratorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='generator-owner', password='Safe-Generator!829')
        cls.other = User.objects.create_user(username='generator-other')
        cls.profile = UserProfile.objects.create(user=cls.user)
        cls.preference = OutfitPreference.objects.create(user=cls.user)
        cls.categories = {slot:ClothingCategory.objects.create(name='Generator '+slot, slot=slot) for slot in ['top','bottom','dress','shoes','outerwear','accessory','other']}
        cls.black = ClothingColor.objects.create(name='Generator black', hex_code='#000000')
        cls.white = ClothingColor.objects.create(name='Generator white', hex_code='#FFFFFF')
        cls.top = cls.item('top','Top',comfort=5)
        cls.top2 = cls.item('top','Second top',comfort=1)
        cls.bottom = cls.item('bottom','Trousers')
        cls.shoes = cls.item('shoes','Shoes')
        cls.dress = cls.item('dress','Dress')
        cls.outer = cls.item('outerwear','Coat',warmth=5)
        cls.foreign = cls.item('top','Secret',user=cls.other)

    @classmethod
    def item(cls, slot, name, **kwargs):
        defaults = {'user':cls.user,'category':cls.categories[slot],'name':name,'comfort':3,'warmth':3,'styles':['casual'],'fit':'regular'}
        defaults.update(kwargs)
        item=ClothingItem.objects.create(**defaults)
        item.colors.add(cls.black)
        return item

    def setUp(self):
        self.client=APIClient(); self.client.force_authenticate(self.user)

    def generate(self, payload=None):
        return self.client.post('/api/outfits/generate/',payload or {},format='json')

    def test_generated_real_owned_items_and_valid_skeletons(self):
        response=self.generate({'count':5})
        self.assertEqual(response.status_code,201)
        self.assertEqual(response.data['count'],5)
        sets=[]
        for result in response.data['results']:
            sets.append(tuple(sorted(result['items'])))
            self.assertNotIn(self.foreign.pk,result['items'])
            slots=[ClothingItem.objects.get(pk=pk).category.slot for pk in result['items']]
            self.assertIn('shoes',slots)
            self.assertTrue(('dress' in slots and 'top' not in slots and 'bottom' not in slots) or ('top' in slots and 'bottom' in slots and 'dress' not in slots))
            self.assertEqual(set(result['items']),{item['id'] for item in result['item_details']})
            self.assertTrue(Outfit.objects.filter(pk=result['id'],user=self.user).exists())
            self.assertTrue(result['generation']['explanation'])
        self.assertEqual(len(sets),len(set(sets)))
        scores=[r['generation']['score'] for r in response.data['results']]
        self.assertEqual(scores,sorted(scores,reverse=True))

    def test_required_excluded_and_unavailable_applied_first(self):
        self.top2.is_available=False; self.top2.save()
        response=self.generate({'required_items':[self.top.pk], 'excluded_items':[self.dress.pk]})
        self.assertEqual(response.status_code,201)
        for result in response.data['results']:
            self.assertIn(self.top.pk,result['items'])
            self.assertNotIn(self.top2.pk,result['items'])
            self.assertNotIn(self.dress.pk,result['items'])

    def test_invalid_ids_do_not_leak_ownership(self):
        for field in ['required_items','excluded_items']:
            foreign=self.generate({field:[self.foreign.pk]})
            absent=self.generate({field:[9999999]})
            self.assertEqual(foreign.status_code,400)
            self.assertEqual(foreign.data,absent.data)
        self.assertFalse(Outfit.objects.exists())

    def test_contradictory_requirements_and_invalid_schema(self):
        cases=[{'required_items':[self.top.pk],'excluded_items':[self.top.pk]}, {'required_items':[self.top.pk,self.top2.pk]}, {'required_items':[self.dress.pk,self.bottom.pk]}, {'required_items':[self.top.pk,self.top.pk]}, {'count':10}, {'count':0}, {'temperature_c':100}, {'temperature_c':'NaN'}, {'preferred_colors':[999999]}, {'unknown':'ignored?'}]
        for payload in cases:
            with self.subTest(payload=payload):
                self.assertEqual(self.generate(payload).status_code,400)
        self.assertFalse(Outfit.objects.exists())

    def test_required_unavailable_or_season_mismatch(self):
        self.top.is_available=False; self.top.save()
        self.assertEqual(self.generate({'required_items':[self.top.pk]}).status_code,400)
        self.top.is_available=True; self.top.season='summer'; self.top.save()
        self.assertEqual(self.generate({'required_items':[self.top.pk],'season':'winter'}).status_code,400)
        self.preference.excluded_categories.add(self.categories['top'])
        self.assertEqual(self.generate({'required_items':[self.top2.pk]}).status_code,400)

    def test_excluded_categories_and_seasons(self):
        self.preference.excluded_categories.add(self.categories['dress'])
        self.top.season='summer'; self.top.save()
        response=self.generate({'season':'winter'})
        self.assertEqual(response.status_code,201)
        for result in response.data['results']:
            self.assertNotIn(self.dress.pk,result['items'])
            self.assertNotIn(self.top.pk,result['items'])
            self.assertIn(self.top2.pk,result['items'])

    def test_cold_temperature_requires_outerwear(self):
        response=self.generate({'temperature_c':5})
        self.assertEqual(response.status_code,201)
        self.assertTrue(all(self.outer.pk in r['items'] for r in response.data['results']))
        self.outer.is_available=False; self.outer.save()
        empty=self.generate({'temperature_c':5})
        self.assertEqual(empty.status_code,200)
        self.assertEqual(empty.data['count'],0)
        self.assertTrue(empty.data['messages'])

    def test_profile_sensitivity_affects_layer_requirement(self):
        self.profile.cold_sensitivity=5; self.profile.save()
        response=self.generate({'temperature_c':13})
        self.assertTrue(all(self.outer.pk in r['items'] for r in response.data['results']))
        self.assertEqual(response.data['results'][0]['generation']['effective_temperature_c'],9)

    def test_missing_weather_renormalizes_weights_and_notes_are_honest(self):
        response=self.generate({'notes':'Хочу официальный образ'})
        self.assertEqual(response.data['weights']['weather'],0)
        self.assertAlmostEqual(sum(response.data['weights'].values()),100)
        self.assertTrue(any('не интерпретируется' in text for text in response.data['messages']))
        for result in response.data['results']:
            self.assertIsNone(result['generation']['criteria']['weather'])
            self.assertEqual(result['generation']['temperature_source'],'none')

    def test_custom_weights_and_comfort_ranking(self):
        weights={'comfort':100,'weather':0,'style':0,'colors':0,'preferences':0}
        response=self.generate({'weights':weights,'required_items':[self.bottom.pk],'excluded_items':[self.outer.pk]})
        self.assertEqual(response.status_code,201)
        self.assertIn(self.top.pk,response.data['results'][0]['items'])
        self.assertNotIn(self.top2.pk,response.data['results'][0]['items'])
        generation=response.data['results'][0]['generation']
        self.assertEqual(generation['score'],generation['criteria']['comfort'])
        bad=self.generate({'weights':dict(weights,comfort=99)})
        self.assertEqual(bad.status_code,400)
        only_weather={'comfort':0,'weather':100,'style':0,'colors':0,'preferences':0}
        self.assertEqual(self.generate({'weights':only_weather}).status_code,400)

    def test_saved_comfort_priority_changes_weights(self):
        self.preference.comfort_priority=100; self.preference.save()
        response=self.generate({'temperature_c':20})
        self.assertEqual(response.data['weights']['comfort'],50)
        response=self.generate({'temperature_c':20,'comfort_priority':0})
        self.assertEqual(response.data['weights']['comfort'],20)

    def test_style_and_color_preferences_affect_ranking(self):
        self.top.styles=['formal']; self.top.save()
        self.top2.styles=['sport']; self.top2.save()
        weights={'comfort':0,'weather':0,'style':100,'colors':0,'preferences':0}
        response=self.generate({'style':'FORMAL','weights':weights,'required_items':[self.bottom.pk]})
        self.assertIn(self.top.pk,response.data['results'][0]['items'])
        self.top2.colors.set([self.white])
        self.preference.preferred_colors.set([self.white])
        self.preference.disliked_colors.set([self.black])
        weights={'comfort':0,'weather':0,'style':0,'colors':0,'preferences':100}
        response=self.generate({'weights':weights,'required_items':[self.bottom.pk]})
        self.assertIn(self.top2.pk,response.data['results'][0]['items'])
        self.assertEqual(self.generate({'preferred_colors':[self.black.pk]}).status_code,400)

    def test_layering_conflict_rejected(self):
        self.outer.fit='slim'; self.outer.save()
        self.top.fit='oversized'; self.top.save()
        response=self.generate({'required_items':[self.outer.pk,self.top.pk]})
        self.assertEqual(response.status_code,400)
        response=self.generate({'required_items':[self.top.pk], 'temperature_c':5})
        self.assertEqual(response.data['count'],0)

    def test_empty_and_insufficient_wardrobe_no_fakes(self):
        self.client.force_authenticate(self.other)
        response=self.generate()
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data['results'],[])
        self.assertFalse(Outfit.objects.filter(user=self.other).exists())
        self.client.force_authenticate(self.user)
        response=self.generate({'excluded_items':[self.top2.pk,self.dress.pk,self.outer.pk]})
        self.assertEqual(response.data['count'],1)
        self.assertTrue(any('только 1' in text for text in response.data['messages']))

    def test_repeat_requests_have_identical_order_and_scores(self):
        first=self.generate().data['results']
        second=self.generate().data['results']
        self.assertEqual([r['items'] for r in first],[r['items'] for r in second])
        self.assertEqual([r['generation']['score'] for r in first],[r['generation']['score'] for r in second])

    def test_history_favorites_and_edit_invalidates_score(self):
        result=self.generate().data['results'][0]
        self.assertEqual(self.client.get(f"/api/outfits/{result['id']}/").status_code,200)
        self.assertEqual(self.client.post('/api/saved-outfits/',{'outfit':result['id']}).status_code,201)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f"/api/outfits/{result['id']}/").status_code,404)
        self.assertEqual(self.client.post('/api/saved-outfits/',{'outfit':result['id']}).status_code,400)
        self.client.force_authenticate(self.user)
        response=self.client.patch(f"/api/outfits/{result['id']}/",{'items':[self.top.pk]},format='json')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data['generation'],{})

    def test_unknown_measurements_are_not_invented(self):
        self.top.comfort=None; self.top.warmth=None; self.top.styles=[]; self.top.save()
        response=self.generate({'temperature_c':20,'required_items':[self.top.pk]})
        self.assertTrue(response.data['results'][0]['generation']['warnings'])

    def test_anonymous_denied(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.generate().status_code,403)

    def test_wardrobe_size_bound(self):
        ClothingItem.objects.bulk_create([ClothingItem(user=self.user,name='Extra',category=self.categories['top']) for _ in range(501)])
        self.assertEqual(self.generate().status_code,400)
        self.assertFalse(Outfit.objects.exists())

    def test_beam_reports_pruning(self):
        for i in range(55):
            self.item('top',f'Candidate {i}')
        response=self.generate()
        self.assertEqual(response.status_code,201)
        self.assertTrue(response.data['search']['pruned'])

    def test_color_harmony_and_db_constraints(self):
        self.assertGreater(color_pair('#000000','#00FF00'),color_pair('#0000FF','#00FF00'))
        self.assertEqual(color_pair('#FF0000','#FF0000'),90)
        with self.assertRaises(IntegrityError),transaction.atomic():
            ClothingItem.objects.filter(pk=self.top.pk).update(comfort=6)
        with self.assertRaises(IntegrityError),transaction.atomic():
            ClothingItem.objects.filter(pk=self.top.pk).update(warmth=0)

    def test_changed_or_deleted_item_marks_score_stale(self):
        result=self.generate().data['results'][0]
        url=f"/api/outfits/{result['id']}/"
        self.assertFalse(result['generation_is_stale'])
        item=ClothingItem.objects.get(pk=result['items'][0])
        item.name='Edited'; item.save()
        self.assertTrue(self.client.get(url).data['generation_is_stale'])
        item.delete()
        self.assertTrue(self.client.get(url).data['generation_is_stale'])

    def test_invalid_json_and_weights_rejected(self):
        self.assertEqual(self.client.post('/api/outfits/generate/', '{"temperature_c":NaN}', content_type='application/json').status_code,400)
        weights={'comfort':35,'weather':25,'style':20,'colors':15,'preferences':5,'imaginary':1}
        self.assertEqual(self.generate({'weights':weights}).status_code,400)
