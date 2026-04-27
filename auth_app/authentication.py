from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """Reads JWT from the 'access_token' cookie; falls back to the Authorization header."""

    def authenticate(self, request):
        access_token = request.COOKIES.get("access_token")

        if access_token:
            validated_token = self.get_validated_token(access_token)
            user = self.get_user(validated_token)
            return (user, validated_token)

        return super().authenticate(request)
