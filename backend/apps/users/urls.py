from django.urls import path

from .views import LoginView, LogoutView, RegisterView, SsoBoundTokenRefreshView, SsoExchangeView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", SsoBoundTokenRefreshView.as_view(), name="auth-refresh"),
    path("sso/", SsoExchangeView.as_view(), name="auth-sso"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
]
