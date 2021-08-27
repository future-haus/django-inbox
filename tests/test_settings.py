from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
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
                    'message_keys': ['default'],
                    'skip_app_push': [],
                    'skip_email': [],
                    'skip_web_push': [],
                    'skip_sms': []
                }
            ],
            # Callable that returns the Firebase push notification key so that a user can be sent pushes, or None
            # if one doesn't exist for the user.
            'CHECK_IS_EMAIL_VERIFIED': True,
            'BACKENDS': {
                'APP_PUSH': 'inbox.core.app_push.backends.locmem.AppPushBackend',
                'APP_PUSH_CONFIG': {
                    'GOOGLE_FCM_SERVER_KEY': 'abc'
                }
            },
            'TESTING_MEDIUM_OUTPUT_PATH': None,
            'DISABLE_NEW_DATA_SILENT_APP_PUSH': False,
            'MESSAGE_CREATE_FAIL_SILENTLY': True,
            'HOOKS_MODULE': None,
            'PROCESS_NEW_MESSAGES_LIMIT': 25,
            'PROCESS_NEW_MESSAGE_LOGS_LIMIT': 25,
            'PER_USER_MESSAGES_MAX_AGE': None,
            'PER_USER_MESSAGES_MAX_COUNT': None,
            'PER_USER_MESSAGES_MIN_AGE': None,
            'PER_USER_MESSAGES_MIN_COUNT': None,
        }

        with self.settings(INBOX_CONFIG={}):
            inbox_settings.get_config.cache_clear()
            settings = inbox_settings.get_config()

            self.maxDiff = 4096
            self.assertEqual(settings, default_config)

    def test_test_app_settings(self):

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
                    'message_keys': ['default', 'hook_fails_throws_exception'],
                    'skip_app_push': [],
                    'skip_email': ['hook_fails_throws_exception'],
                    'skip_web_push': [],
                    'skip_sms': []
                },
                {
                    'id': 'inbox_only',
                    'label': 'Inbox Only',
                    'description': 'Inbox only messages.',
                    'is_preference': False,
                    'use_preference': None,
                    'preference_defaults': {
                        'app_push': None,
                        'email': None,
                        'sms': None,
                        'web_push': None
                    },
                    'data': {},
                    'message_keys': ['welcome', 'key_with_no_template'],
                    'skip_app_push': [],
                    'skip_email': [],
                    'skip_web_push': [],
                    'skip_sms': []
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
                    'message_keys': ['new_account', 'account_updated'],
                    'skip_app_push': [],
                    'skip_email': [],
                    'skip_web_push': [],
                    'skip_sms': []
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
                    'message_keys': ['new_friend_request', 'friend_request_accepted'],
                    'skip_app_push': [],
                    'skip_email': [],
                    'skip_web_push': [],
                    'skip_sms': []
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
                    'message_keys': ['important_update'],
                    'skip_app_push': [],
                    'skip_email': [],
                    'skip_web_push': [],
                    'skip_sms': []
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
                    'message_keys': ['push_only'],
                    'skip_app_push': [],
                    'skip_email': [],
                    'skip_web_push': [],
                    'skip_sms': []
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
                    'message_keys': ['all_mediums_off'],
                    'skip_app_push': [],
                    'skip_email': [],
                    'skip_web_push': [],
                    'skip_sms': []
                },
                {
                    'id': 'group_with_skip_push',
                    'label': 'Group with skip push',
                    'description': "This group has one key that won't send an app push.",
                    'is_preference': True,
                    'use_preference': None,
                    'preference_defaults': {
                        'app_push': True,
                        'email': True,
                        'web_push': None,
                        'sms': None
                    },
                    'data': {},
                    'message_keys': ['group_with_skip_push', 'group_with_skip_push_2', 'group_with_skip_push_3'],
                    'skip_app_push': ['group_with_skip_push_2', 'group_with_skip_push_3'],
                    'skip_email': ['group_with_skip_push_3'],
                    'skip_web_push': [],
                    'skip_sms': []
                }
            ],
            'CHECK_IS_EMAIL_VERIFIED': True,
            'BACKENDS': {
                'APP_PUSH': 'inbox.core.app_push.backends.locmem.AppPushBackend',
                'APP_PUSH_CONFIG': {
                    'GOOGLE_FCM_SERVER_KEY': 'abc'
                }
            },
            'TESTING_MEDIUM_OUTPUT_PATH': None,
            'DISABLE_NEW_DATA_SILENT_APP_PUSH': False,
            'MESSAGE_CREATE_FAIL_SILENTLY': True,
            'HOOKS_MODULE': 'tests.hooks',
            'PROCESS_NEW_MESSAGES_LIMIT': 25,
            'PROCESS_NEW_MESSAGE_LOGS_LIMIT': 25,
            'PER_USER_MESSAGES_MAX_AGE': None,
            'PER_USER_MESSAGES_MAX_COUNT': None,
            'PER_USER_MESSAGES_MIN_AGE': None,
            'PER_USER_MESSAGES_MIN_COUNT': None,
        }

        inbox_settings.get_config.cache_clear()
        settings = inbox_settings.get_config()

        self.maxDiff = 8192
        self.assertEqual(settings, test_app_config)
