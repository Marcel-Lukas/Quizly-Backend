from django.urls import path
from .views import RegistrationView, CookieTokenObtainPairView, CookieRefreshView
from rest_framework_simplejwt.views import TokenRefreshView


from . import views

urlpatterns = [
    path('registration/', RegistrationView.as_view(), name='registration'),
    path('token/', CookieTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CookieRefreshView.as_view(), name='token_refresh'),


    path('hello/', views.HelloWorldView.as_view(), name='hello'),
]

