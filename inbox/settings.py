from functools import lru_cache

from django.conf import settings


CONFIG_DEFAULTS = {
    # Message groups are used to organize the messages and provide preferences and their defaults
    'MESSAGE_GROUPS': [
        {
            'id': 'default',
            'label': 'News and Updates',
            'description': 'General news and updates.',
            'is_preference': True,
            'use_preference': None,  # If is_preference is False, this defines which group to use as preference
            'preference_defaults': {  # If you want to disable a preference, just use None
                'app_push': True,
                'email': True,
                'sms': True,
                'web_push': True
            },
            'message_keys': ['default']
        }
    ],
    # Callable that returns the Firebase push notification key so that a user can be sent pushes, or None
    # if one doesn't exist for the user.
    'APP_PUSH_NOTIFICATION_KEY_GETTER': None,
    'BACKENDS': {
        'APP_PUSH': 'inbox.core.app_push.backends.firebase.FirebaseBackend'
    }
}


@lru_cache()
def get_config():
    USER_CONFIG = getattr(settings, "INBOX_CONFIG", {})
    CONFIG = CONFIG_DEFAULTS.copy()
    CONFIG.update(USER_CONFIG)
    return CONFIG
