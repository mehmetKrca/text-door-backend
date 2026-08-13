"""
Django settings for core project.
"""

from pathlib import Path
from datetime import timedelta
import environ
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DEBUG', default=False)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

# Sentry hata takibi (DSN tanımlı değilse yerel geliştirmede başlatılmaz)
SENTRY_DSN = env('SENTRY_DSN', default='')
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,  # KVKK: kişisel veri Sentry'ye gönderilmesin
    )


# Application definition
INSTALLED_APPS = [
    # 🎯 JAZZMIN ADMIN TEMASI (django.contrib.admin'den ÖNCE gelmeli!)
    'jazzmin',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # --- YENİ EKLENEN KÜTÜPHANELER (SAAS MOTORU) ---
    'rest_framework',              # API altyapısı
    'rest_framework.authtoken',    # Token oluşturucu
    'rest_framework_simplejwt',    # JWT token motoru
    'dj_rest_auth',                # API üzerinden giriş/çıkış yönetimi
    'dj_rest_auth.registration',   # API üzerinden kayıt yönetimi
    'corsheaders',                 # React ile Django'yu konuşturacak güvenlik köprüsü
    
    # Allauth (Sosyal Giriş İçin Zorunlu)
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google', # Google Sağlayıcısı

    # --- KENDİ UYGULAMALARIMIZ ---
    'users',                       # App adı 'users'
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', # React haberleşmesi için EN ÜSTE EKLENDİ
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Allauth zorunlu ara katmanı
    'allauth.account.middleware.AccountMiddleware', 
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'tr'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'

# ==============================================================================
# 🎨 JAZZMIN ADMIN PANELİ ÖZELLEŞTİRME AYARLARI (eWindoore)
# ==============================================================================
JAZZMIN_SETTINGS = {
    "site_title": "eWindoore Admin",
    "site_header": "eWindoore SaaS",
    "site_brand": "eWindoore Yönetim",
    "welcome_sign": "eWindoore Atölye & Müşteri Yönetim Paneline Hoş Geldiniz",
    "copyright": "eWindoore Dijital Çizim Sistemleri",
    "search_model": "users.CustomUser",
    "topmenu_links": [
        {"name": "Ana Sayfa", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"model": "users.CustomUser"},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.Group": "fas fa-users",
        "users.CustomUser": "fas fa-user-tie",
        "users.Proje": "fas fa-drafting-compass",
        "users.FiyatTablosu": "fas fa-tags",
        "sites.Site": "fas fa-globe",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "changeform_format": "horizontal_tabs",
    "show_ui_builder": False,
}

JAZZMIN_UI_TWEAKS = {
    "navbar": "navbar-dark navbar-navy",
    "sidebar": "sidebar-dark-navy",
    "theme": "default",
    "accent": "accent-primary",
}

# ==============================================================================
# 🚀 eWindoore SAAS - ÖZEL GÜVENLİK VE GOOGLE GİRİŞ (AUTH) AYARLARI 🚀
# ==============================================================================

# React (Frontend) tarafının bu Django sunucusuna istek atabilmesi için izinler
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=['http://localhost:5173'])
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# REST Framework Ayarları (JWT Token ile güvenli giriş ve Hız Sınırlandırması TAM EKLENDİ)
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',    # Giriş yapmamış kullanıcıları denetler
        'rest_framework.throttling.UserRateThrottle',    # Giriş yapmış kullanıcıları denetler
        'rest_framework.throttling.ScopedRateThrottle',  # 'login' gibi özel etiketleri denetler
    ],
    'DEFAULT_THROTTLE_RATES': {
        'login': '10/min',   # Brute-force koruması: Dakikada maksimum 10 deneme
        'anon': '1000/day',  # Kayıtsız kullanıcılar için günlük genel istek limiti
        'user': '5000/day',  # Giriş yapmış kullanıcılar için günlük genel istek limiti
    }
}

# dj-rest-auth JWT Kullanımını Aktifleştirme
REST_AUTH = {
    'USE_JWT': True,
    'JWT_AUTH_COOKIE': 'ewindoore-auth',
    'JWT_AUTH_REFRESH_COOKIE': 'ewindoore-refresh-token',
}

# Simple JWT Ayarları
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
}

# Allauth için zorunlu site ID
SITE_ID = 1

# Google ile ilk girişte kullanıcıya otomatik Firma atayan adapter
SOCIALACCOUNT_ADAPTER = 'users.adapters.CustomSocialAccountAdapter'

# Kimlik Doğrulama Motorları (Normal giriş + Google/Sosyal giriş)
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Özel Kullanıcı Modeli Tanımı
AUTH_USER_MODEL = 'users.CustomUser'

# Django-allauth Güncel Kuralları (Uyarıları Temizleyen Versiyon)
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'none'

# ==============================================================================
# SOCIALACCOUNT AYARLARI (400 Bad Request Hatasını Kesen Tam Konfigürasyon)
# ==============================================================================
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': env('GOOGLE_CLIENT_ID'),
            'secret': env('GOOGLE_CLIENT_SECRET'),
            'key': ''
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
    }
}

# ==============================================================================
# 📝 PRODUCTION LOGGING (GÜNCELLENMİŞ VE KESİN HATA TAKİBİ)
# ==============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'errors.log',
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'style': '{',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}