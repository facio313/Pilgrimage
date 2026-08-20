from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import LoginView, RegisterView, SsoExchangeView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("sso/", SsoExchangeView.as_view(), name="auth-sso"),
]
