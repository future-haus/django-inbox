import os
from unittest import skip

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from faker import Faker
from tests.test import TransactionTestCase
import responses

from inbox import settings as inbox_settings
from inbox.constants import MessageLogStatus
from inbox.core import app_push
from inbox.core.app_push import AppPushMessage
from inbox.models import Message
from inbox.test.utils import AppPushTestCaseMixin
from inbox.utils import process_new_messages, process_new_message_logs

User = get_user_model()
fake = Faker()


class FirebaseAppPushBackendTestCase(AppPushTestCaseMixin, TransactionTestCase):

    user = None

    def setUp(self):
        super().setUp()
        self.user = User.objects.create(email=fake.ascii_email, email_verified_on=timezone.now().date())
        self.fake_notification_key = 'fake-notification-key'
        self.user.device_group.notification_key = self.fake_notification_key
        self.user.device_group.save()

    @responses.activate
    @skip
    def test_send_messages(self):
        os.environ['GOOGLE_CLOUD_PROJECT'] = 'future-haus'

        message = Message.objects.create(user=self.user, key='default')
        process_new_messages()
        message_log = message.logs.all()[0]

        connection = app_push.get_connection('inbox.core.app_push.backends.firebase.AppPushBackend', dry_run=True)

        responses.add(responses.POST, 'https://oauth2.googleapis.com/token',
                      json={'access_token': '0987654321poiuytrewq'})

        responses.add(responses.POST, 'https://fcm.googleapis.com/v1/projects/future-haus/messages:send',
                      json={'name': 'projects/future-haus/messages/0:1500415314455276%31bd1c9631bd1c96'})

        AppPushMessage(self.user, 'Test Subject', 'Test Body', data={}, connection=connection,
                       message_log=message_log).send()

        responses.replace(responses.POST, 'https://fcm.googleapis.com/v1/projects/future-haus/messages:send',
                          json={'error': {'details': [
                              {'@type': 'type.googleapis.com/google.firebase.fcm.v1.FcmError',
                               'errorCode': 'UNREGISTERED'}
                          ]}}, status=404)

        message = Message.objects.create(user=self.user, key='default')
        process_new_messages()
        message_log = message.logs.all()[0]

        AppPushMessage(self.user, 'Test Subject', 'Test Body', data={}, connection=connection,
                       message_log=message_log).send()

        # notification key should be null now
        self.user.device_group.refresh_from_db()
        self.assertIsNone(self.user.device_group.notification_key)
        message_log.refresh_from_db()
        self.assertEqual(message_log.status, MessageLogStatus.FAILED)

        responses.replace(responses.POST, 'https://fcm.googleapis.com/v1/projects/future-haus/messages:send',
                          json={'error': {'details': [
                              {'@type': 'type.googleapis.com/google.firebase.fcm.v1.FcmError',
                               'errorCode': 'THIRD_PARTY_AUTH_ERROR'}
                          ]}}, status=401)

        AppPushMessage(self.user, 'Test Subject', 'Test Body', data={}, connection=connection).send()

        responses.replace(responses.POST, 'https://fcm.googleapis.com/v1/projects/future-haus/messages:send',
                          json={'error': {'details': [
                              {'@type': 'type.googleapis.com/google.firebase.fcm.v1.FcmError',
                               'errorCode': 'SENDER_ID_MISMATCH'}
                          ]}}, status=403)

        AppPushMessage(self.user, 'Test Subject', 'Test Body', data={}, connection=connection).send()

        responses.replace(responses.POST, 'https://fcm.googleapis.com/v1/projects/future-haus/messages:send',
                          json={'error': {'details': [
                              {'@type': 'type.googleapis.com/google.firebase.fcm.v1.FcmError',
                               'errorCode': 'QUOTA_EXCEEDED'}
                          ]}}, status=429)

        AppPushMessage(self.user, 'Test Subject', 'Test Body', data={}, connection=connection).send()

    @responses.activate
    def test_send_message_with_nested_data(self):
        os.environ['GOOGLE_CLOUD_PROJECT'] = 'future-haus'

        message = Message.objects.create(user=self.user, key='default', data={'foo': 'bar', 'foo2': {}})
        process_new_messages()
        message_log = message.logs.all()[0]

        inbox_settings.get_config.cache_clear()
        INBOX_CONFIG = settings.INBOX_CONFIG.copy()
        INBOX_CONFIG['BACKENDS']['APP_PUSH_CONFIG'] = {
            'GOOGLE_FCM_SENDER_ID': 'abc',
            'GOOGLE_FCM_SENDER_KEY': 'abc'
        }
        with self.settings(INBOX_CONFIG=INBOX_CONFIG):
            connection = app_push.get_connection('inbox.core.app_push.backends.firebase.AppPushBackend', dry_run=True)

            responses.add(responses.POST, 'https://fcm.googleapis.com/fcm/send',
                          json={'success': 1})

            AppPushMessage(self.user, 'Test Subject', 'Test Body', data={'foo': 'bar', 'foo2': {}},
                           connection=connection, message_log=message_log).send()

    # @responses.activate
    # def test_save_message_process_for_push(self):
    #
    #     # We use lru_cache on INBOX_CONFIG, clear it out
    #     inbox_settings.get_config.cache_clear()
    #     # Then override the INBOX_CONFIG setting, we'll add a new message group and see it we get the expected return
    #     INBOX_CONFIG = settings.INBOX_CONFIG.copy()
    #     INBOX_CONFIG['BACKENDS']['APP_PUSH'] = 'inbox.core.app_push.backends.firebase.AppPushBackend'
    #     with self.settings(INBOX_CONFIG=INBOX_CONFIG):
    #         Message.objects.create(user=self.user, key='default')
    #
    #         responses.add(responses.POST, 'https://oauth2.googleapis.com/token',
    #                       json={'access_token': '0987654321poiuytrewq'})
    #
    #         responses.add(responses.POST, 'https://fcm.googleapis.com/v1/projects/future-haus/messages:send',
    #                       json={'name': 'projects/future-haus/messages/0:1500415314455276%31bd1c9631bd1c96'})
    #
    #         process_new_messages()
    #
    #     inbox_settings.get_config().cache_clear()
    #
