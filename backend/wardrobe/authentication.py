from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import InvalidToken

class SafeTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        try:
            return super().validate(attrs)
        except get_user_model().DoesNotExist:
            raise InvalidToken('Account no longer exists.') from None
