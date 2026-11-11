from django.conf import settings
from django.core.files.uploadhandler import FileUploadHandler, StopUpload

class LimitedUploadHandler(FileUploadHandler):
    def __init__(self, request):
        super().__init__(request)
        self.total = 0
    def receive_data_chunk(self, raw_data, start):
        self.total += len(raw_data)
        if self.total > settings.PHOTO_MAX_BYTES:
            self.request.photo_too_large = True
            raise StopUpload(connection_reset=False)
        return raw_data
    def file_complete(self, file_size):
        return None

class PhotoUploadMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        if request.path.startswith('/api/'):
            request.upload_handlers.insert(0, LimitedUploadHandler(request))
        return self.get_response(request)
