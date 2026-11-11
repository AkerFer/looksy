from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator

FIT_CHOICES = [(x, x) for x in ["unknown", "regular", "slim", "relaxed", "oversized"]]

class User(AbstractUser):
    pass

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=100, blank=True)
    preferred_style = models.CharField(max_length=80, blank=True)
    city = models.CharField(max_length=150, blank=True)
    latitude = models.DecimalField(max_digits=8, decimal_places=5, null=True, blank=True, validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.DecimalField(max_digits=8, decimal_places=5, null=True, blank=True, validators=[MinValueValidator(-180), MaxValueValidator(180)])
    cold_sensitivity = models.PositiveSmallIntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])
    heat_sensitivity = models.PositiveSmallIntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(cold_sensitivity__gte=1, cold_sensitivity__lte=5, heat_sensitivity__gte=1, heat_sensitivity__lte=5), name='valid_temperature_sensitivity'), models.CheckConstraint(condition=(models.Q(latitude__isnull=True,longitude__isnull=True) | models.Q(latitude__isnull=False,longitude__isnull=False,latitude__gte=-90,latitude__lte=90,longitude__gte=-180,longitude__lte=180)), name='profile_coordinates_pair')]

class ClothingCategory(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slot = models.CharField(max_length=12, choices=[(x,x) for x in ['top','bottom','dress','outerwear','shoes','accessory','other']])
    def __str__(self): return self.name

class ClothingColor(models.Model):
    name = models.CharField(max_length=50, unique=True)
    hex_code = models.CharField(max_length=7, validators=[RegexValidator(r'^#[0-9a-fA-F]{6}$')])
    def __str__(self): return self.name

class Owned(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        abstract = True
        indexes = [models.Index(fields=['user', '-created_at'])]

class ClothingItem(Owned):
    name = models.CharField(max_length=150)
    category = models.ForeignKey(ClothingCategory, on_delete=models.PROTECT)
    colors = models.ManyToManyField(ClothingColor, blank=True)
    description = models.TextField(blank=True, max_length=2000)
    season = models.CharField(max_length=12, choices=[(x,x) for x in ['all','summer','winter','spring','autumn']], default='all')
    is_available = models.BooleanField(default=True)
    brand = models.CharField(max_length=100, blank=True)
    material = models.CharField(max_length=100, blank=True)
    fit = models.CharField(max_length=12, choices=FIT_CHOICES, default='unknown')
    styles = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    comfort = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    warmth = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])

    class Meta(Owned.Meta):
        constraints = [models.CheckConstraint(condition=models.Q(comfort__isnull=True) | models.Q(comfort__gte=1, comfort__lte=5), name='valid_clothing_comfort'), models.CheckConstraint(condition=models.Q(warmth__isnull=True) | models.Q(warmth__gte=1, warmth__lte=5), name='valid_clothing_warmth')]
        indexes = Owned.Meta.indexes + [models.Index(fields=['user', 'category', 'is_available']), models.Index(fields=['user', 'season'])]

class Outfit(Owned):
    generation = models.JSONField(default=dict, blank=True)
    name = models.CharField(max_length=150)
    items = models.ManyToManyField(ClothingItem, through='OutfitItem')

class OutfitItem(models.Model):
    outfit = models.ForeignKey(Outfit, on_delete=models.CASCADE, related_name='outfit_items')
    clothing_item = models.ForeignKey(ClothingItem, on_delete=models.CASCADE)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['outfit','clothing_item'], name='unique_outfit_item')]

class OutfitPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    style = models.CharField(max_length=80, blank=True)
    styles = models.JSONField(default=list, blank=True)
    preferred_colors = models.ManyToManyField(ClothingColor, blank=True, related_name='preferred_by')
    disliked_colors = models.ManyToManyField(ClothingColor, blank=True, related_name='disliked_by')
    preferred_fit = models.CharField(max_length=12, choices=FIT_CHOICES, default='unknown')
    comfort_priority = models.PositiveSmallIntegerField(default=50, validators=[MinValueValidator(0), MaxValueValidator(100)])
    excluded_categories = models.ManyToManyField(ClothingCategory, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(comfort_priority__gte=0, comfort_priority__lte=100), name='valid_comfort_priority')]

class OutfitFeedback(Owned):
    outfit = models.ForeignKey(Outfit, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1),MaxValueValidator(5)])
    comment = models.CharField(max_length=1000, blank=True)
    class Meta(Owned.Meta):
        constraints = [models.UniqueConstraint(fields=['user','outfit'], name='unique_feedback'), models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name='valid_rating')]

class SavedOutfit(Owned):
    outfit = models.ForeignKey(Outfit, on_delete=models.CASCADE)
    class Meta(Owned.Meta):
        constraints = [models.UniqueConstraint(fields=['user','outfit'], name='unique_saved_outfit')]

class WeatherContext(Owned):
    latitude = models.DecimalField(max_digits=8, decimal_places=5, validators=[MinValueValidator(-90),MaxValueValidator(90)])
    longitude = models.DecimalField(max_digits=8, decimal_places=5, validators=[MinValueValidator(-180),MaxValueValidator(180)])
    temperature_c = models.FloatField(validators=[MinValueValidator(-100),MaxValueValidator(70)])
    condition = models.CharField(max_length=80)
    apparent_temperature_c = models.FloatField(null=True, blank=True)
    precipitation_probability = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MaxValueValidator(100)])
    wind_speed_kmh = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0)])
    forecast_for = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=30, default='manual')
    observed_at = models.DateTimeField()
    class Meta(Owned.Meta):
        constraints = [models.CheckConstraint(condition=models.Q(latitude__gte=-90,latitude__lte=90,longitude__gte=-180,longitude__lte=180), name='valid_coordinates'), models.CheckConstraint(condition=models.Q(precipitation_probability__isnull=True) | models.Q(precipitation_probability__gte=0,precipitation_probability__lte=100),name='valid_rain_probability'),models.CheckConstraint(condition=models.Q(wind_speed_kmh__isnull=True) | models.Q(wind_speed_kmh__gte=0),name='valid_wind_speed')]


class PrivatePhoto(Owned):
    clothing = models.OneToOneField(ClothingItem, on_delete=models.CASCADE, null=True, blank=True, related_name='photo')
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='avatar')
    original = models.FileField(upload_to='private/')
    processed = models.FileField(upload_to='private/')
    analysis = models.JSONField(default=dict)

    class Meta(Owned.Meta):
        constraints = [models.CheckConstraint(condition=(models.Q(clothing__isnull=False, profile__isnull=True) | models.Q(clothing__isnull=True, profile__isnull=False)), name='photo_has_one_parent')]


class OutfitCalendarEntry(Owned):
    outfit = models.ForeignKey(Outfit, on_delete=models.CASCADE, related_name='calendar_entries')
    date = models.DateField()
    note = models.CharField(max_length=300, blank=True)

    class Meta(Owned.Meta):
        constraints = [models.UniqueConstraint(fields=['user','date'], name='one_outfit_per_user_day')]
        indexes = Owned.Meta.indexes + [models.Index(fields=['user','date'])]
