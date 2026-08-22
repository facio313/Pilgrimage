import os
from pathlib import Path

from decouple import config

from common.edge_secret import load_edge_secret
from config.auth_mode import resolve_portfolio_auth_contract

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# GeoDjango - GDAL/GEOS/PROJ paths (macOS Homebrew)
GDAL_LIBRARY_PATH = os.environ.get("GDAL_LIBRARY_PATH", "/opt/homebrew/lib/libgdal.dylib")
GEOS_LIBRARY_PATH = os.environ.get("GEOS_LIBRARY_PATH", "/opt/homebrew/lib/libgeos_c.dylib")

SECRET_KEY = config("SECRET_KEY")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    # Local apps
    "apps.users",
    "apps.spots",
    "apps.routes",
    "apps.visits",
    "apps.reviews",
    "apps.kto_sync",
]

AUTH_USER_MODEL = "users.User"

AUTHENTICATION_BACKENDS = [
    "apps.users.backends.EmailBackend",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": config("POSTGRES_DB", default="pilgrimage"),
        "USER": config("POSTGRES_USER", default=""),
        "PASSWORD": config("POSTGRES_PASSWORD", default=""),
        "HOST": config("POSTGRES_HOST", default="localhost"),
        "PORT": config("POSTGRES_PORT", default="5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.users.authentication.SsoBoundJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "apps.users.permissions.IsPortfolioUser",
    ],
    "EXCEPTION_HANDLER": "common.exceptions.custom_exception_handler",
}

# SimpleJWT
from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
}

# The Git branch is the source of truth for authentication. Local checkouts use
# the repository resolver; packaged runtimes receive both canonical variables
# explicitly from their build/deployment boundary.
_portfolio_environment = {
    name: value
    for name in ("PORTFOLIO_BRANCH", "PORTFOLIO_AUTH_MODE", "GITHUB_REF_NAME")
    if (value := config(name, default=None)) is not None
}
_portfolio_auth = resolve_portfolio_auth_contract(
    base_dir=BASE_DIR,
    environment=_portfolio_environment,
    legacy_sso_name="PILGRIMAGE_SSO_ENABLED",
    legacy_sso_value=config("PILGRIMAGE_SSO_ENABLED", default=None),
    build_mode=config("PORTFOLIO_BUILD_AUTH_MODE", default=None),
    build_contract_path=Path("/etc/portfolio-auth-build"),
)
PORTFOLIO_BRANCH = _portfolio_auth.branch
PORTFOLIO_AUTH_MODE = _portfolio_auth.mode
PILGRIMAGE_SSO_ENABLED = _portfolio_auth.sso_enabled
PILGRIMAGE_SSO_EDGE_SECRET_FILE = config("PILGRIMAGE_SSO_EDGE_SECRET_FILE", default="")
PILGRIMAGE_SSO_EDGE_SECRET = load_edge_secret(
    enabled=PILGRIMAGE_SSO_ENABLED,
    file_path=PILGRIMAGE_SSO_EDGE_SECRET_FILE,
    fallback=config("PILGRIMAGE_SSO_EDGE_SECRET", default=""),
)
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")
