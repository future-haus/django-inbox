from django.contrib.auth import get_user_model
from django.test import TestCase
from faker import Faker

from inbox import settings as inbox_settings

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
                    'data': {},
                    'message_keys': ['default']
                }
            ],
            # Callable that returns the Firebase push notification key so that a user can be sent pushes, or None
            # if one doesn't exist for the user.
            'APP_PUSH_NOTIFICATION_KEY_GETTER': None,
            'BACKENDS': {
                'APP_PUSH': 'inbox.core.app_push.backends.locmem.AppPushBackend'
            },
            'TESTING_MEDIUM_OUTPUT_PATH': None,
            'DISABLE_NEW_DATA_SILENT_APP_PUSH': False,
            'MESSAGE_CREATE_FAIL_SILENTLY': True,
            'HOOKS_MODULE': None
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
                    'data': {},
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
                    'data': {},
                    'message_keys': ['new_account', 'account_updated']
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
                    'data': {},
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
                    'data': {},
                    'message_keys': ['important_update']
                },
                {
                    'id': 'push_only_group',
                    'label': 'Push only group',
                    'description': "Receive notifications about push only.",
                    'is_preference': True,
                    'use_preference': None,
                    'preference_defaults': {
                        'app_push': True,
                        'email': None,
                        'sms': None,
                        'web_push': None
                    },
                    'data': {},
                    'message_keys': ['push_only']
                },
                {
                    'id': 'group_with_all_mediums_off',
                    'label': 'Group with All Mediums Off',
                    'description': "This group should not show up in preferences.",
                    'is_preference': True,
                    'use_preference': None,
                    'preference_defaults': {
                        'app_push': None,
                        'email': None,
                        'web_push': None,
                        'sms': None
                    },
                    'data': {},
                    'message_keys': ['all_mediums_off']
                }
            ],
            'APP_PUSH_NOTIFICATION_KEY_GETTER': 'tests.models.get_notification_key',
            'BACKENDS': {
                'APP_PUSH': 'inbox.core.app_push.backends.locmem.AppPushBackend'
            },
            'TESTING_MEDIUM_OUTPUT_PATH': None,
            'DISABLE_NEW_DATA_SILENT_APP_PUSH': False,
            'MESSAGE_CREATE_FAIL_SILENTLY': True,
            'HOOKS_MODULE': 'tests.hooks'
        }

        inbox_settings.get_config.cache_clear()
        settings = inbox_settings.get_config()

        self.maxDiff = 8192
        self.assertEqual(settings, test_app_config)
