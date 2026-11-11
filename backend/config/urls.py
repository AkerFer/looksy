from wardrobe.weather_api import LocationsView, ForecastView
from wardrobe.stylist_api import StylistView
from wardrobe.generation_api import GenerateOutfitsView
from wardrobe.photos import ClothingFromPhotoView, PrivatePhotoView, OriginalPhotoView, AvatarView, OriginalAvatarView
from django.contrib import admin
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenBlacklistView
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from wardrobe import views as v
router = DefaultRouter()
for prefix, view, name in [('calendar',v.CalendarViewSet,'calendar'),('clothing',v.ClothingViewSet,'clothing'),('outfits',v.OutfitViewSet,'outfit'),('feedback',v.FeedbackViewSet,'feedback'),('saved-outfits',v.SavedViewSet,'saved'),('weather',v.WeatherViewSet,'weather'),('categories',v.CategoryViewSet,'category'),('colors',v.ColorViewSet,'color')]:
    router.register(prefix,view,basename=name)
urlpatterns = [
    path('api/locations/', LocationsView.as_view()),
    path('api/weather/forecast/', ForecastView.as_view()),
    path('api/stylist/', StylistView.as_view()),
    path('api/outfits/generate/', GenerateOutfitsView.as_view()),
    path('api/clothing/from-photo/', ClothingFromPhotoView.as_view()),
    path('api/clothing/<int:pk>/photo/', PrivatePhotoView.as_view()),
    path('api/clothing/<int:pk>/photo/original/', OriginalPhotoView.as_view()),
    path('api/profile/avatar/', AvatarView.as_view()),
    path('api/profile/avatar/original/', OriginalAvatarView.as_view()),
path('admin/',admin.site.urls),path('api/auth/token/',TokenObtainPairView.as_view()),path('api/auth/token/refresh/',TokenRefreshView.as_view()),path('api/auth/token/logout/',TokenBlacklistView.as_view()),path('health/',v.health),path('api/auth/session/',v.SessionView.as_view()),path('api/auth/register/',v.RegisterView.as_view()),path('api/account/',v.AccountView.as_view()),path('api/profile/',v.ProfileView.as_view()),path('api/preferences/',v.PreferenceView.as_view()),path('api/',include(router.urls))]
