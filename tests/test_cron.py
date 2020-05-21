from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from faker import Faker

from inbox.core import app_push
from inbox.models import Message, MessageLog
from inbox.test.utils import AppPushTestCaseMixin
from tests.test import TransactionTestCase

User = get_user_model()
fake = Faker()


class CronTestCase(AppPushTestCaseMixin, TransactionTestCase):

    user = None

    def setUp(self):
        super().setUp()
        self.user = User.objects.create(email=fake.ascii_email, email_verified_on=timezone.now().date())
        self.user.device_group.notification_key = 'fake-notification-key'
        self.user.device_group.save()

    def test_cron_process_new_messages(self):

        self.assertEqual(MessageLog.objects.count(), 0)

        message = Message.objects.create(user=self.user, key='default', fail_silently=False)

        response = self.get('/cron/process_new_messages')
        self.assertHTTP200(response)

        response = self.get('/cron/process_new_message_logs')
        self.assertHTTP200(response)

        self.assertEqual(len(app_push.outbox), 3)
        self.assertEqual(len(mail.outbox), 1)

        self.assertEqual(message.subject, "Default Subject Line's Text")
