from django.contrib.auth import get_user_model
from django.core import mail
from faker import Faker
from tests.test import TestCase

from inbox.core import app_push
from inbox.models import Message, MessageLog
from inbox.test.utils import AppPushTestCaseMixin

User = get_user_model()
fake = Faker()


class CronTestCase(AppPushTestCaseMixin, TestCase):

    user = None

    def setUp(self):
        super().setUp()
        self.user = User.objects.create(email=fake.ascii_email)

    def test_cron_process_new_messages(self):

        self.assertEqual(MessageLog.objects.count(), 0)

        Message.objects.create(user=self.user, key='default')

        response = self.get('/cron/process_new_messages')
        self.assertHTTP200(response)

        self.assertEqual(len(app_push.outbox), 1)
        self.assertEqual(len(mail.outbox), 1)
