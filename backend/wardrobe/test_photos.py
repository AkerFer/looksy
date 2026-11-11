from io import BytesIO
from pathlib import Path
import tempfile
from unittest.mock import patch
from PIL import Image, ImageDraw
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from .models import User, UserProfile, ClothingCategory, ClothingItem, PrivatePhoto
from .imaging import process, recognize, palette


def picture(fmt='PNG', size=(160,160), exif=False):
    image = Image.new('RGB', size, 'white')
    ImageDraw.Draw(image).rectangle((size[0]//4,size[1]//4,size[0]*3//4,size[1]*3//4), fill='red')
    stream = BytesIO()
    kwargs = {}
    if exif:
        meta = Image.Exif(); meta[270] = 'PRIVATE METADATA'; meta[274] = 6
        kwargs['exif'] = meta
    image.save(stream, format=fmt, **kwargs)
    return SimpleUploadedFile('untrusted.'+fmt.lower(), stream.getvalue(), content_type='application/octet-stream')


class PhotoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='photo-owner', password='Photo-Pass!8291')
        cls.other = User.objects.create_user(username='photo-other')
        cls.profile = UserProfile.objects.create(user=cls.user)
        category = ClothingCategory.objects.first()
        cls.item = ClothingItem.objects.create(user=cls.user, name='My shirt', category=category)
        cls.foreign = ClothingItem.objects.create(user=cls.other, name='Private shirt', category=category)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.config = override_settings(MEDIA_ROOT=self.directory.name, U2NET_HOME=self.directory.name+'/no-model', CLOTHING_ONNX_MODEL='', CLOTHING_ONNX_LABELS='')
        self.config.enable()
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(self.config.disable)
        self.client = APIClient(); self.client.force_authenticate(self.user)
        self.url = f'/api/clothing/{self.item.pk}/photo/'

    def upload(self, url=None, image=None):
        return self.client.post(url or self.url, {'image':image or picture()}, format='multipart')

    def test_upload_and_private_stream(self):
        response = self.upload()
        self.assertEqual(response.status_code,201)
        self.assertEqual(response.data['analysis']['recognition']['status'],'unavailable')
        self.assertIn(response.data['analysis']['background'],['grabcut','unchanged'])
        for url, size in [(self.url,(1024,1024)),(self.url+'original/',(160,160))]:
            stream=self.client.get(url)
            self.assertEqual(stream.status_code,200)
            self.assertEqual(stream['Cache-Control'],'private, no-store')
            self.assertEqual(stream['Content-Type'],'image/png')
            image=Image.open(BytesIO(b''.join(stream.streaming_content)))
            self.assertEqual(image.size,size)
        item=self.client.get(f'/api/clothing/{self.item.pk}/').data
        self.assertEqual(item['photo']['url'],self.url)
        self.assertNotIn('private/', str(item['photo']))
        self.assertTrue(response.data['analysis']['colors'])
        self.assertEqual(PrivatePhoto.objects.get().user,self.user)

    def test_jpeg_webp_and_metadata_removed(self):
        for fmt in ['JPEG','WEBP']:
            with self.subTest(fmt=fmt):
                with self.captureOnCommitCallbacks(execute=True):
                    self.assertEqual(self.upload(image=picture(fmt,exif=True)).status_code,201)
                photo=PrivatePhoto.objects.get()
                with photo.original.open('rb') as stream:
                    clean=Image.open(stream)
                    self.assertFalse(clean.getexif())
                    self.assertNotIn('exif',clean.info)
                    self.assertEqual(clean.format,'PNG')

    def test_foreign_and_anonymous_denied(self):
        self.upload()
        self.client.force_authenticate(self.other)
        for url in [self.url,self.url+'original/']:
            self.assertEqual(self.client.get(url).status_code,404)
        self.assertEqual(self.upload().status_code,404)
        self.assertEqual(self.client.delete(self.url).status_code,404)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code,403)
        self.assertEqual(self.upload().status_code,403)
        self.assertEqual(self.client.get('/media/'+PrivatePhoto.objects.get().original.name).status_code,404)

    def test_validation_invalid_animated_and_limits(self):
        for content in [b'<svg onload="x"/>',b'not an image',b'']:
            image=SimpleUploadedFile('x.jpg',content,content_type='image/jpeg')
            self.assertEqual(self.upload(image=image).status_code,400)
        self.assertEqual(self.upload(image=picture('GIF')).status_code,400)
        self.assertEqual(self.upload(image=picture(size=(16,16))).status_code,400)
        with override_settings(PHOTO_MAX_PIXELS=1000):
            self.assertEqual(self.upload().status_code,400)
        huge=SimpleUploadedFile('large.jpg',b'x'*(5*1024*1024+1),content_type='image/jpeg')
        self.assertEqual(self.upload(image=huge).status_code,400)
        stream=BytesIO()
        Image.new('RGB',(64,64),'red').save(stream,format='PNG',save_all=True,append_images=[Image.new('RGB',(64,64),'blue')],duration=100,loop=0)
        self.assertEqual(self.upload(image=SimpleUploadedFile('a.png',stream.getvalue())).status_code,400)
        self.assertFalse(PrivatePhoto.objects.exists())

    def test_only_one_image_accepted(self):
        self.assertEqual(self.client.post(self.url,{'image':[picture(),picture()]},format='multipart').status_code,400)
        self.assertEqual(self.client.post(self.url,{'image':picture(),'user':self.other.pk},format='multipart').status_code,400)
        self.assertEqual(self.client.post(self.url,{},format='multipart').status_code,400)

    def test_replacement_deletion_and_account_cleanup(self):
        self.upload()
        old=PrivatePhoto.objects.get()
        old_paths=[old.original.path,old.processed.path]
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.upload().status_code,201)
        self.assertTrue(all(not Path(p).exists() for p in old_paths))
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.upload('/api/profile/avatar/').status_code,201)
        paths=[p for photo in PrivatePhoto.objects.all() for p in [photo.original.path,photo.processed.path]]
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.delete('/api/account/',{'password':'Photo-Pass!8291'},format='json').status_code,204)
        self.assertFalse(PrivatePhoto.objects.exists())
        self.assertTrue(all(not Path(p).exists() for p in paths))

    def test_item_and_photo_delete_remove_files(self):
        for delete_item in [False,True]:
            self.upload()
            paths=[PrivatePhoto.objects.get().original.path,PrivatePhoto.objects.get().processed.path]
            with self.captureOnCommitCallbacks(execute=True):
                url=f'/api/clothing/{self.item.pk}/' if delete_item else self.url
                self.assertEqual(self.client.delete(url).status_code,204)
            self.assertTrue(all(not Path(p).exists() for p in paths))
        self.assertFalse(PrivatePhoto.objects.exists())

    def test_avatar_is_private(self):
        response=self.upload('/api/profile/avatar/')
        self.assertEqual(response.status_code,201)
        self.assertEqual(response.data['analysis']['recognition']['status'],'not_requested')
        self.assertIsNotNone(self.client.get('/api/profile/').data['avatar'])
        stream=self.client.get('/api/profile/avatar/')
        self.assertEqual(Image.open(BytesIO(b''.join(stream.streaming_content))).size,(512,512))
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/profile/avatar/').status_code,404)

    def test_storage_failure_preserves_previous_photo(self):
        self.upload()
        photo=PrivatePhoto.objects.get()
        paths=[photo.original.path,photo.processed.path]
        with patch('django.core.files.storage.FileSystemStorage.save',side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError):
                self.upload()
        self.assertEqual(PrivatePhoto.objects.get().pk,photo.pk)
        self.assertTrue(all(Path(p).exists() for p in paths))

    def test_avatar_parent_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            PrivatePhoto.objects.create(user=self.user,clothing=self.item,profile=self.profile)

    def test_empty_photo_returns_404(self):
        self.assertEqual(self.client.get(self.url).status_code,404)
        self.assertEqual(self.client.get(self.url+'original/').status_code,404)

    def test_color_extraction_and_aspect_ratio(self):
        image=Image.new('RGBA',(80,160),(255,0,0,255))
        self.assertEqual(palette(image)[0]['hex'],'#FF0000')
        _, output, _ = process(picture(size=(80,160)),avatar=True)
        image=Image.open(BytesIO(output))
        box=image.getchannel('A').getbbox()
        self.assertAlmostEqual((box[2]-box[0])/(box[3]-box[1]),.5,places=2)

    def test_classifier_error_is_explicit(self):
        with override_settings(CLOTHING_ONNX_MODEL='/missing.onnx',CLOTHING_ONNX_LABELS='/missing.json'):
            result=recognize(Image.new('RGBA',(64,64),'red'))
        self.assertEqual(result['status'],'error')
        self.assertIsNone(result['category'])

    def test_create_card_from_photo(self):
        response=self.client.post('/api/clothing/from-photo/',{'image':picture()},format='multipart')
        self.assertEqual(response.status_code,201)
        item=ClothingItem.objects.get(pk=response.data['id'])
        self.assertEqual(item.user,self.user)
        self.assertEqual(item.category.slot,'other')
        self.assertIsNotNone(response.data['photo'])
        self.assertEqual(response.data['photo']['analysis']['recognition']['status'],'unavailable')
        self.assertEqual(self.client.patch(f'/api/clothing/{item.pk}/',{'name':'Моя футболка','season':'summer'},format='json').status_code,200)
        before=ClothingItem.objects.count()
        self.assertEqual(self.client.post('/api/clothing/from-photo/',{'image':SimpleUploadedFile('x.png',b'broken')},format='multipart').status_code,400)
        self.assertEqual(ClothingItem.objects.count(),before)

    def test_small_image_fills_processed_canvas(self):
        from .imaging import center
        source=Image.new('RGBA',(40,80),(255,0,0,255))
        box=center(source).getchannel('A').getbbox()
        self.assertAlmostEqual(box[3]-box[1],1024*.88,delta=1)
        self.assertAlmostEqual((box[2]-box[0])/(box[3]-box[1]),.5,places=2)
