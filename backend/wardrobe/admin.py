from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from . import models as m
admin.site.register(m.User, UserAdmin)
for model in [m.UserProfile,m.ClothingCategory,m.ClothingColor,m.ClothingItem,m.Outfit,m.OutfitItem,m.OutfitPreference,m.OutfitFeedback,m.SavedOutfit,m.WeatherContext]:
    admin.site.register(model)
