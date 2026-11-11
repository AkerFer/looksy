from django.apps import AppConfig

class WardrobeConfig(AppConfig):
    name = 'wardrobe'
    def ready(self):
        from . import signals  # noqa: F401
