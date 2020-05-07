from unittest.mock import MagicMock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from faker import Faker
from inbox import settings as inbox_settings
from inbox import signals
from inbox.constants import MessageLogStatus
from inbox.core import app_push

from inbox.models import Message, get_message_group_default, MessageMedium, MessageLog
from inbox.test.utils import AppPushTestCaseMixin
from inbox.utils import process_new_messages, process_new_message_logs

User = get_user_model()
fake = Faker()


class MessageTestCase(AppPushTestCaseMixin, TestCase):

    user = None

    def setUp(self):
        super().setUp()
        self.user = User.objects.create(email=fake.ascii_email)

    def test_can_save_message(self):

        message = Message.objects.create(user=self.user, key='default')

        self.assertEqual(message.user.email, self.user.email)
        self.assertEqual(message.group, {'id': 'default', 'label': 'Updates', 'data': {}})
        self.assertEqual(message.key, 'default')

    def test_unread_count_signal_gets_proper_data(self):
        handler = MagicMock()
        signals.unread_count.connect(handler, sender=Message)

        # Do what it takes to trigger the signal
        Message.objects.create(user=self.user, key='default')

        # Assert the signal was called only once with the args
        handler.assert_called_once_with(signal=signals.unread_count, count=1, sender=Message)

        # Do what it takes to trigger the signal
        Message.objects.create(user=self.user, key='default')

        # Assert the signal was called only once with the args
        handler.assert_called_with(signal=signals.unread_count, count=2, sender=Message)

    def test_unread_count_signal_gets_proper_data_after_mark_read(self):

        handler = MagicMock()
        signals.unread_count.connect(handler, sender=Message)

        # Do what it takes to trigger the signal
        Message.objects.create(user=self.user, key='default')
        Message.objects.create(user=self.user, key='default')
        Message.objects.create(user=self.user, key='default')

        # Assert the signal was called only once with the args
        handler.assert_called_with(signal=signals.unread_count, count=3, sender=Message)

        handler = MagicMock()
        signals.unread_count.connect(handler, sender=Message)

        Message.objects.mark_all_read(self.user.id)

        # Assert the signal was called only once with the args
        handler.assert_called_once_with(signal=signals.unread_count, count=0, sender=Message)

    def test_save_message_with_invalid_key(self):

        # We use lru_cache on INBOX_CONFIG, clear it out
        inbox_settings.get_config.cache_clear()
        # Then override the INBOX_CONFIG setting, we'll add a new message group and see it we get the expected return
        INBOX_CONFIG = settings.INBOX_CONFIG.copy()
        INBOX_CONFIG['MESSAGE_CREATE_FAIL_SILENTLY'] = False
        with self.settings(INBOX_CONFIG=INBOX_CONFIG):
            with self.assertRaises(ValidationError) as context:
                Message.objects.create(user=self.user, key='non_existent_key')

            self.assertTrue('Subject template for "non_existent_key" does not exist.' in context.exception.messages[0])

        inbox_settings.get_config.cache_clear()

        # Verify that you can adjust fail_silently on a per call basis
        with self.assertRaises(ValidationError) as context:
            Message.objects.create(user=self.user, key='non_existent_key', fail_silently=False)

        self.assertTrue('Subject template for "non_existent_key" does not exist.' in context.exception.messages[0])

    def test_create_message_verify_log_exists(self):

        self.assertEqual(MessageLog.objects.count(), 0)

        message = Message.objects.create(user=self.user, key='default')

        message_logs = MessageLog.objects.filter(message=message)

        used = []
        for k, message_log in enumerate(message_logs):
            # Tested this way because order can change
            self.assertTrue(message_log.medium in (MessageMedium.EMAIL, MessageMedium.APP_PUSH) and message_log.medium not in used)
            self.assertEqual(message.pk, message_log.message_id)
            used.append(message_log.medium)

    def test_defined_message_id_exists(self):

        self.assertEqual(MessageLog.objects.count(), 0)

        now_str = timezone.now().strftime('%Y%m%d')
        test_message_id = f'default_{self.user.pk}_{now_str}'
        Message.objects.create(user=self.user, key='default', message_id=test_message_id)

        existing_message_ids, missing_message_ids = Message.objects.exists(test_message_id)

        self.assertEqual(existing_message_ids, set([test_message_id]))
        self.assertEqual(missing_message_ids, set())

        existing_message_ids, missing_message_ids = Message.objects.exists([test_message_id, '123'])

        self.assertEqual(existing_message_ids, set([test_message_id]))
        self.assertEqual(missing_message_ids, set(['123']))

    def test_create_message_process_message_logs(self):

        self.assertEqual(MessageLog.objects.count(), 0)

        Message.objects.create(user=self.user, key='default')

        process_new_messages()
        process_new_message_logs()

        self.assertEqual(len(app_push.outbox), 3)
        self.assertEqual(len(mail.outbox), 1)

    def test_create_message_process_message_logs_user_has_push_off(self):

        groups = self.user.message_preferences.groups.copy()
        groups[0]['app_push'] = False
        self.user.message_preferences.groups = groups
        self.user.message_preferences.save()

        self.assertEqual(MessageLog.objects.count(), 0)

        message = Message.objects.create(user=self.user, key='default')

        process_new_messages()

        # Verify two message log entries
        self.assertTrue(len(message.logs.all()), 2)

        process_new_message_logs()

        self.assertEqual(len(app_push.outbox), 2)
        self.assertEqual(len(mail.outbox), 1)

        for message_log in message.logs.all():
            if message_log.medium == MessageMedium.APP_PUSH:
                self.assertTrue(message_log.status, MessageLogStatus.SKIPPED_FOR_PREF)
            if message_log.medium == MessageMedium.EMAIL:
                self.assertTrue(message_log.status, MessageLogStatus.SENT)

    def test_verify_app_push_template_falls_back(self):

        self.assertEqual(MessageLog.objects.count(), 0)

        Message.objects.create(user=self.user, key='push_only')

        process_new_messages()

    def test_create_message_fail_silently(self):

        message = Message.objects.create(user=self.user)

        self.assertIsNone(message)

    def test_message_is_cancelled_before_sending_but_schedules_future(self):
        Message.objects.create(user=self.user, key='new_account', fail_silently=False)

        messages_count = Message.objects.count()
        self.assertEqual(messages_count, 1)

        process_new_messages()
        process_new_message_logs()

        message_logs_count = MessageLog.objects.count()
        messages_count = Message.objects.count()

        self.assertEqual(message_logs_count, 0)
        self.assertEqual(messages_count, 2)
