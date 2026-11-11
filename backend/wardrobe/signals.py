from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import PrivatePhoto


def delete_files(files):
    for storage, name in files:
        if name:
            storage.delete(name)


@receiver(post_delete, sender=PrivatePhoto)
def remove_photo_files(sender, instance, using, **kwargs):
    files = [(instance.original.storage, instance.original.name), (instance.processed.storage, instance.processed.name)]
    transaction.on_commit(lambda: delete_files(files), using=using, robust=True)
