from uuid import uuid4
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import ClothingItem, ClothingCategory, UserProfile, PrivatePhoto
from .imaging import process
from .signals import delete_files


class PhotoUploadSerializer(serializers.Serializer):
    image = serializers.FileField(allow_empty_file=False)


def metadata(photo, base):
    return {'url':base, 'original_url':base+'original/', 'analysis':photo.analysis, 'version':photo.pk}


def store_photo(user, parent, original, processed, analysis, avatar=False):
    stored = []
    try:
        with transaction.atomic():
            # Lock the parent to serialize replacements of the same photo.
            parent = type(parent).objects.select_for_update().get(pk=parent.pk, user=user)
            link = {'profile':parent} if avatar else {'clothing':parent}
            old = PrivatePhoto.objects.filter(**link).first()
            if old:
                old.delete()
            photo = PrivatePhoto(user=user, analysis=analysis, **link)
            for name, payload in [('original',original), ('processed',processed)]:
                field = getattr(photo,name)
                field.save(uuid4().hex+'.png', ContentFile(payload), save=False)
                stored.append((field.storage, field.name))
            photo.save()
    except Exception:
        delete_files(stored)
        raise
    return photo


class PrivatePhotoView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    avatar = False
    original = False

    def parent(self, request, pk=None, lock=False):
        model = UserProfile if self.avatar else ClothingItem
        if self.avatar:
            UserProfile.objects.get_or_create(user=request.user)
        qs = model.objects.filter(user=request.user)
        if lock:
            qs = qs.select_for_update()
        return get_object_or_404(qs, **({} if self.avatar else {'pk':pk}))

    def photo(self, parent):
        return get_object_or_404(PrivatePhoto, **({'profile':parent} if self.avatar else {'clothing':parent}), user=parent.user)

    def get(self, request, pk=None):
        photo = self.photo(self.parent(request, pk))
        field = photo.original if self.original else photo.processed
        try:
            response = FileResponse(field.open('rb'), content_type='image/png')
        except FileNotFoundError:
            raise Http404 from None
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Content-Security-Policy'] = "default-src 'none'; sandbox"
        return response

    def post(self, request, pk=None):
        self.parent(request, pk)  # Reject inaccessible objects before decoding any pixels.
        data = request.data
        if getattr(request._request, 'photo_too_large', False):
            return Response({'image':['Изображение должно быть не больше 5 МБ.']}, status=400)
        if set(data) != {'image'} or len(request.FILES.getlist('image')) != 1:
            return Response({'image':['Передайте ровно один файл в поле image.']}, status=400)
        serializer = PhotoUploadSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        original, processed, analysis = process(serializer.validated_data['image'], avatar=self.avatar)
        parent = self.parent(request, pk)
        photo = store_photo(request.user, parent, original, processed, analysis, avatar=self.avatar)
        return Response(metadata(photo,request.path), status=201)

    def delete(self, request, pk=None):
        with transaction.atomic():
            parent = self.parent(request, pk, lock=True)
            self.photo(parent).delete()
        return Response(status=204)


class AvatarView(PrivatePhotoView):
    avatar = True


class OriginalPhotoView(PrivatePhotoView):
    original = True
    http_method_names = ['get', 'head', 'options']


class OriginalAvatarView(AvatarView):
    original = True
    http_method_names = ['get', 'head', 'options']


class PhotoCreateSerializer(PhotoUploadSerializer):
    name = serializers.CharField(max_length=150, required=False, default='Новая вещь')
    category = serializers.PrimaryKeyRelatedField(queryset=ClothingCategory.objects.all(), required=False)


class ClothingFromPhotoView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        data = request.data
        if getattr(request._request, 'photo_too_large', False):
            return Response({'image':['Изображение должно быть не больше 5 МБ.']}, status=400)
        if set(data) - {'image','name','category'} or len(request.FILES.getlist('image')) != 1:
            return Response({'image':['Передайте один файл image, необязательные name и category.']}, status=400)
        serializer = PhotoCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        original, processed, analysis = process(values['image'])
        photo = None
        try:
            with transaction.atomic():
                from .models import ClothingCategory
                category = values.get('category')
                if category is None:
                    category = ClothingCategory.objects.get(name='Другие вещи', slot='other')
                item = ClothingItem.objects.create(user=request.user, name=values['name'], category=category)
                photo = store_photo(request.user, item, original, processed, analysis)
        except Exception:
            if photo:
                delete_files([(photo.original.storage, photo.original.name), (photo.processed.storage, photo.processed.name)])
            raise
        from .serializers import ClothingItemSerializer
        return Response(ClothingItemSerializer(item, context={'request':request}).data, status=201)
