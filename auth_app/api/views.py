from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import RegistrationSerializer, CustomTokenObtainPairSerializer


class RegistrationView(APIView):
    """
    API endpoint that allows new users to register.

    Accessible without authentication. Delegates validation and
    object creation to `RegistrationSerializer`.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """Validate the request data and create a new user account."""
        serializer = RegistrationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response({'detail': 'User created successfully!'}, status=status.HTTP_201_CREATED)



class CookieTokenObtainPairView(TokenObtainPairView):
    """
    JWT login endpoint that stores tokens in HttpOnly cookies.

    Replaces the default JSON token response with two HttpOnly cookies
    (`access_token` and `refresh_token`) to prevent JavaScript access
    and reduce XSS exposure.
    """
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        """
        Authenticate the user and issue access and refresh tokens as
        HttpOnly cookies instead of returning them in the response body.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh = serializer.validated_data["refresh"]
        access = serializer.validated_data["access"]

        response = Response({"detail": "Login successfully",
                             "user": {
                                 "id": serializer.user.id,
                                 "username": serializer.user.username,
                                 "email": serializer.user.email
                             }})

        response.set_cookie(
            key="access_token",
            value=str(access),
            httponly=True,
            secure=True,
            samesite="Lax"
        )

        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite="Lax"
        )

        return response



class CookieTokenRefreshView(TokenRefreshView):
    """
    JWT token-refresh endpoint that reads the refresh token from a cookie.

    Expects a valid `refresh_token` HttpOnly cookie set by
    `CookieTokenObtainPairView` and issues a new `access_token` cookie.
    """

    def post(self, request, *args, **kwargs):
        """
        Read the refresh token from the cookie instead of the request body
        and return a new access token as an HttpOnly cookie.
        """
        refresh_token = request.COOKIES.get("refresh_token")

        if not refresh_token:
            return Response(
                {"error": "Refresh token not found!"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = self.get_serializer(data={"refresh": refresh_token})

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            return Response(
                {"error": "Invalid refresh token!"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        access_token = serializer.validated_data.get("access")

        response = Response({"detail": "Token refreshed"}, status=status.HTTP_200_OK)

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="Lax"
        )

        return response



class LogoutView(APIView):
    """
    API endpoint that logs out the current user.

    Clears both the `access_token` and `refresh_token` HttpOnly cookies,
    effectively ending the session on the client side.
    """

    def post(self, request):
        """Delete the authentication cookies to log the user out."""
        response = Response(
            {"detail": "Logged out successfully. All session tokens have been invalidated."}, status=status.HTTP_200_OK)

        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return response


