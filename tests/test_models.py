from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase
from faker import Faker
from inbox import signals
from inbox.constants import MessageLogStatus
from inbox.core import app_push

from inbox.models import Message, get_message_group_default, MessageMedium, MessageLog
from inbox.utils import process_new_messages, AppPushTestCaseMixin

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
        self.assertEqual(message.group, get_message_group_default())
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

        with self.assertRaises(ValidationError) as context:
            Message.objects.create(user=self.user, key='non_existent_key')

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

    def test_create_message_process_message_logs(self):

        self.assertEqual(MessageLog.objects.count(), 0)

        Message.objects.create(user=self.user, key='default')

        process_new_messages()

        self.assertEqual(len(app_push.outbox), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_create_message_process_message_logs_user_has_push_off(self):

        groups = self.user.message_preferences.groups.copy()
        groups[0]['app_push'] = False
        self.user.message_preferences.groups = groups
        self.user.message_preferences.save()

        # TODO Django's test runner manages resetting mail.outbox, our app push one needs a custom TestCase so that
        #  we can do the same, until then manually handle it
        app_push.outbox = []
        self.assertEqual(MessageLog.objects.count(), 0)

        message = Message.objects.create(user=self.user, key='default')

        # Verify two message log entries
        self.assertTrue(len(message.messagelog_set.all()), 2)

        process_new_messages()

        self.assertEqual(len(app_push.outbox), 0)
        self.assertEqual(len(mail.outbox), 1)

        for message_log in message.messagelog_set.all():
            if message_log.medium == MessageMedium.APP_PUSH:
                self.assertTrue(message_log.status, MessageLogStatus.SKIPPED_FOR_PREF)
            if message_log.medium == MessageMedium.EMAIL:
                self.assertTrue(message_log.status, MessageLogStatus.SENT)
