from unittest.mock import MagicMock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase
from faker import Faker
from inbox import signals
from inbox.constants import MessageLogStatus
from inbox.core import app_push

from inbox import settings as inbox_settings
from inbox.models import Message, get_message_group_default, MessageMedium, MessageLog
from inbox.utils import process_new_messages

User = get_user_model()
fake = Faker()


class SettingsTestCase(TestCase):

    def test_default_settings(self):

        default_config = {
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
                        'sms': None,
                        'web_push': None
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

        with self.settings(INBOX_CONFIG={}):
            inbox_settings.get_config.cache_clear()
            settings = inbox_settings.get_config()

            self.maxDiff = 4096
            self.assertEqual(settings, default_config)

        test_app_config = {
            # Message groups are used to organize the messages and provide preferences and their defaults
            'MESSAGE_GROUPS': [
                {
                    'id': 'default',
                    'label': 'Updates',
                    'description': 'General news and updates.',
                    'is_preference': True,
                    'use_preference': None,
                    'preference_defaults': {
                        'app_push': True,
                        'email': True,
                        'sms': None,
                        'web_push': None
                    },
                    'message_keys': ['default']
                },
                {
                    'id': 'account_updated',
                    'label': 'Account Updated',
                    'description': 'When you update your account.',
                    'is_preference': True,
                    'use_preference': None,
                    'preference_defaults': {
                        'app_push': True,
                        'email': True,
                        'sms': None,
                        'web_push': None
                    },
                    'message_keys': ['account_updated']
                },
                {
                    'id': 'friend_requests',
                    'label': 'Friend Requests',
                    'description': "Receive reminders about friend requests.",
                    'is_preference': True,
                    'use_preference': None,
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
                    'is_preference': True,
                    'use_preference': None,
                    'preference_defaults': {
                        'app_push': True,
                        'email': True,
                        'sms': None,
                        'web_push': None
                    },
                    'message_keys': ['important_update']
                }
            ],
            'APP_PUSH_NOTIFICATION_KEY_GETTER': 'tests.models.get_notification_key',
            'BACKENDS': {
                'APP_PUSH': 'inbox.core.app_push.backends.locmem.AppPushBackend'
            }
        }

        inbox_settings.get_config.cache_clear()
        settings = inbox_settings.get_config()

        self.maxDiff = 4096
        self.assertEqual(settings, test_app_config)
