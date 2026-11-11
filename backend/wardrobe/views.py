from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError as APIValidationError
from rest_framework import serializers
from . import models as m, serializers as s

def health(request): return JsonResponse({'status':'ok'})

@method_decorator(csrf_protect, name='dispatch')
class SessionView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        return Response({'csrfToken':get_token(request), 'authenticated': request.user.is_authenticated})
    def post(self, request):
        username, password = request.data.get('username'), request.data.get('password')
        if not isinstance(username,str) or not isinstance(password,str):
            return Response({'detail':'Username and password required.'},status=400)
        user = authenticate(request, username=username, password=password)
        if user is None: return Response({'detail':'Invalid credentials.'},status=400)
        login(request,user)
        return Response({'id':user.pk,'username':user.username})
    def delete(self, request):
        logout(request)
        return Response(status=204)

class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, validators=m.User._meta.get_field('username').validators)
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    display_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    def validate(self, data):
        try: validate_password(data['password'],m.User(username=data['username'],email=data.get('email','')))
        except ValidationError as exc: raise serializers.ValidationError({'password':exc.messages})
        return data

@method_decorator(csrf_protect, name='dispatch')
class RegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        data = RegisterSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                attributes = dict(data.validated_data)
                display_name = attributes.pop('display_name', '')
                user = m.User.objects.create_user(**attributes)
                m.UserProfile.objects.create(user=user, display_name=display_name)
                m.OutfitPreference.objects.create(user=user)
        except IntegrityError: return Response({'username':['Username already exists.']},status=400)
        return Response({'id':user.pk,'username':user.username},status=201)

class AccountView(APIView):
    def get(self, request): return Response({'id':request.user.pk,'username':request.user.username,'email':request.user.email})
    def delete(self, request):
        if not request.user.check_password(request.data.get('password','')):
            return Response({'detail':'Current password required.'},status=400)
        with transaction.atomic(): request.user.delete()
        logout(request)
        return Response(status=204)

class OwnedViewSet(viewsets.ModelViewSet):
    def get_queryset(self): return self.queryset.filter(user=self.request.user).order_by("-created_at", "-pk")
    def perform_create(self, serializer):
        try:
            with transaction.atomic(): serializer.save(user=self.request.user)
        except IntegrityError: raise APIValidationError('Duplicate or invalid relationship.')
    def perform_update(self, serializer):
        try:
            with transaction.atomic(): serializer.save()
        except IntegrityError: raise APIValidationError('Duplicate or invalid relationship.')

class ClothingViewSet(OwnedViewSet):
    queryset = m.ClothingItem.objects.select_related('category', 'photo').prefetch_related('colors')
    serializer_class = s.ClothingItemSerializer

    def get_queryset(self):
        from .filters import filter_clothing
        queryset = super().get_queryset()
        # Filters affect collections only; detail writes resolve by owner and ID.
        if self.action in ('list', 'summary'):
            return filter_clothing(queryset, self.request.query_params)
        return queryset

    @action(detail=False, methods=['get'])
    def summary(self, request):
        from django.db.models import Count, Q
        queryset = self.get_queryset()
        totals = queryset.aggregate(total=Count('id'), available=Count('id', filter=Q(is_available=True)))
        totals['unavailable'] = totals['total'] - totals['available']
        totals['categories'] = list(queryset.order_by().values('category_id', 'category__name').annotate(count=Count('id')).order_by('category_id'))
        return Response(totals)
class OutfitViewSet(OwnedViewSet):
    queryset = m.Outfit.objects.prefetch_related('items__category', 'items__photo', 'items__colors')
    serializer_class = s.OutfitSerializer
class FeedbackViewSet(OwnedViewSet):
    queryset = m.OutfitFeedback.objects.all()
    serializer_class = s.FeedbackSerializer
class SavedViewSet(OwnedViewSet):
    queryset = m.SavedOutfit.objects.all()
    serializer_class = s.SavedSerializer
class WeatherViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = s.WeatherSerializer
    def get_queryset(self): return m.WeatherContext.objects.filter(user=self.request.user).order_by("-created_at", "-pk")
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = m.ClothingCategory.objects.all().order_by('id')
    serializer_class = s.CategorySerializer
class ColorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = m.ClothingColor.objects.all().order_by('id')
    serializer_class = s.ColorSerializer
class ProfileView(APIView):
    def get_object(self,request): return m.UserProfile.objects.get_or_create(user=request.user)[0]
    def get(self,request): return Response(s.ProfileSerializer(self.get_object(request)).data)
    def patch(self,request):
        serializer = s.ProfileSerializer(self.get_object(request),data=request.data,partial=True)
        serializer.is_valid(raise_exception=True); serializer.save()
        return Response(serializer.data)
class PreferenceView(ProfileView):
    def get_object(self,request): return m.OutfitPreference.objects.get_or_create(user=request.user)[0]
    def get(self,request): return Response(s.PreferenceSerializer(self.get_object(request)).data)
    def patch(self,request):
        serializer = s.PreferenceSerializer(self.get_object(request),data=request.data,partial=True)
        serializer.is_valid(raise_exception=True); serializer.save()
        return Response(serializer.data)


class CalendarViewSet(OwnedViewSet):
    queryset = m.OutfitCalendarEntry.objects.select_related('outfit').prefetch_related('outfit__items__category','outfit__items__photo','outfit__items__colors')
    serializer_class = s.CalendarSerializer
