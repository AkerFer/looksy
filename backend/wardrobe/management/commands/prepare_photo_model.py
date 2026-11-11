import os
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Download and verify rembg u2netp weights.'
    def handle(self, **options):
        os.environ['U2NET_HOME'] = settings.U2NET_HOME
        import pooch
        # Authoritative checksum from the pinned rembg U2netpSession implementation.
        pooch.retrieve('https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx',
                       known_hash='md5:8e83ca70e441ab06c318d82300c84806',
                       fname='u2netp.onnx', path=Path(settings.U2NET_HOME)/'models/u2netp', progressbar=True)
        from wardrobe.imaging import background_session
        background_session.cache_clear()
        background_session(settings.U2NET_HOME)
        self.stdout.write(self.style.SUCCESS('u2netp ready; checksum verified.'))
