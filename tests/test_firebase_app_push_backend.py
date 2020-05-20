from django.contrib.auth import get_user_model
from django.utils import timezone
from faker import Faker

from inbox.core.app_push.backends.firebase import AppPushBackend
from inbox.models import Message
from inbox.test.utils import AppPushTestCaseMixin
from tests.test import TransactionTestCase

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

    def test_notification_key_getter(self):

        self.message = Message.objects.create(user=self.user, key='default')

        notification_key = AppPushBackend().notification_key(self.message)

        self.assertEqual(notification_key, self.fake_notification_key)
