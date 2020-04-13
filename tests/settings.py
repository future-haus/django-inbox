import os

from inbox.constants import MessageMedium

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(PROJECT_DIR)

SECRET_KEY = 'fake-key'

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',

    'inbox',
    'tests',
]

ROOT_URLCONF = 'tests.urls'

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'inbox',
        'USER': 'inbox',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': ''
    },
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
    },
]

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/a/static/'

INBOX_CONFIG = {
    # Message groups are used to organize the messages and provide preferences and their defaults
    'MESSAGE_GROUPS': [
        {
            'id': 'default',
            'label': 'Updates',
            'description': 'General news and updates.',
            'preference_defaults': {
                'email': True,
                'sms': None
            },
            'message_keys': ['default']
        },
        {
            'id': 'account_updated',
            'label': 'Account Updated',
            'description': 'When you update your account.',
            'message_keys': ['account_updated']
        },
        {
            'id': 'friend_requests',
            'label': 'Friend Requests',
            'description': "Receive reminders about friend requests.",
            'preference_defaults': {
                'app_push': True,
                'email': True,
                'sms': True,
                'web_push': True
            },
            'message_keys': ['new_friend_request', 'friend_request_accepted']
        },
        {
            'id': 'important_updates',
            'label': 'Important Updates',
            'description': "Receive notifications about important updates.",
            'preference_defaults': {
                'app_push': True,
                'email': True
            },
            'message_keys': ['important_update']
        }
    ],
    'APP_PUSH_NOTIFICATION_KEY_GETTER': 'tests.models.get_notification_key',
    'BACKENDS': {
        'APP_PUSH': 'inbox.core.app_push.backends.locmem.AppPushBackend'
    }
}

GOOGLE_FCM_SENDER_ID = '12345'
GOOGLE_FCM_SERVER_KEY = '678910'
