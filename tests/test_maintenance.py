import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from faker import Faker
from freezegun import freeze_time

from inbox import settings as inbox_settings
from inbox.models import Message
from inbox.test.utils import InboxTestCaseMixin
from inbox.utils import process_new_messages, process_new_message_logs

User = get_user_model()
Faker.seed()
fake = Faker()


class MaintenanceTestCase(InboxTestCaseMixin, TestCase):

    user = None

    def setUp(self):
        super().setUp()
        email = fake.ascii_email()
        self.user = User.objects.create(email=email, email_verified_on=timezone.now().date(), username=email)
        self.user.device_group.notification_key = 'fake-notification_key'
        self.user.device_group.save()

        inbox_settings.get_config.cache_clear()

    def tearDown(self):
        super().tearDown()

        inbox_settings.get_config.cache_clear()

    def test_maintenance_max_age(self):

        INBOX_CONFIG = settings.INBOX_CONFIG.copy()
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_AGE'] = timezone.timedelta(days=5)
        with self.settings(INBOX_CONFIG=INBOX_CONFIG):

            messages = Message.objects.filter(user=self.user).live()
            self.assertEqual(len(messages), 0)

            messages = Message.objects.filter(user=self.user)
            self.assertEqual(len(messages), 0)

            with freeze_time('2020-01-01'):
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 1)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 1)

            with freeze_time('2020-01-02'):
                # Create another, should be two
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 2)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 2)

            with freeze_time('2020-01-07'):
                # Create another, should still be two since the first one is more than 5 days max age
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 2)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 2)

    def test_maintenance_max_age_with_message_id(self):

        INBOX_CONFIG = settings.INBOX_CONFIG.copy()
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_AGE'] = timezone.timedelta(days=5)
        with self.settings(INBOX_CONFIG=INBOX_CONFIG):

            messages = Message.objects.filter(user=self.user).live()
            self.assertEqual(len(messages), 0)

            messages = Message.objects.filter(user=self.user)
            self.assertEqual(len(messages), 0)

            with freeze_time('2020-01-01'):
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 1)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 1)

            with freeze_time('2020-01-02'):
                # Create another, should be two
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 2)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 2)

            with freeze_time('2020-01-07'):
                # Create another, should still be two since the first one is more than 5 days max age
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 2)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 3)

    def test_maintenance_max_age_min_count(self):

        INBOX_CONFIG = settings.INBOX_CONFIG.copy()
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_AGE'] = timezone.timedelta(days=5)
        INBOX_CONFIG['PER_USER_MESSAGES_MIN_COUNT'] = 3
        with self.settings(INBOX_CONFIG=INBOX_CONFIG):
            messages = Message.objects.filter(user=self.user).live()
            self.assertEqual(len(messages), 0)

            messages = Message.objects.filter(user=self.user)
            self.assertEqual(len(messages), 0)

            with freeze_time('2020-01-01'):
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 1)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 1)

            with freeze_time('2020-01-02'):
                # Create another, should be two
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 2)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 2)

            with freeze_time('2020-01-07'):
                # Create another, should be 3 because the min count saves it
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()

                self.assertEqual(len(messages), 3)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 3)

                # Creating another should keep it at 3 though because it will delete that oldest one now
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 3)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 3)

    def test_maintenance_max_age_min_count_with_message_id(self):

        INBOX_CONFIG = settings.INBOX_CONFIG.copy()
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_AGE'] = timezone.timedelta(days=5)
        INBOX_CONFIG['PER_USER_MESSAGES_MIN_COUNT'] = 3
        with self.settings(INBOX_CONFIG=INBOX_CONFIG):
            messages = Message.objects.filter(user=self.user).live()
            self.assertEqual(len(messages), 0)

            messages = Message.objects.filter(user=self.user)
            self.assertEqual(len(messages), 0)

            with freeze_time('2020-01-01'):
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 1)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 1)

            with freeze_time('2020-01-02'):
                # Create another, should be two
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 2)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 2)

            with freeze_time('2020-01-07'):
                # Create another, should be 3 because the min count saves it
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()

                self.assertEqual(len(messages), 3)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 3)

                # Creating another should keep it at 3 though because it will delete that oldest one now
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 3)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 4)

    def test_maintenance_max_age_min_count_max_count(self):

        INBOX_CONFIG = settings.INBOX_CONFIG.copy()
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_AGE'] = timezone.timedelta(days=5)
        INBOX_CONFIG['PER_USER_MESSAGES_MIN_COUNT'] = 3
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_COUNT'] = 6
        with self.settings(INBOX_CONFIG=INBOX_CONFIG):
            messages = Message.objects.filter(user=self.user).live()
            self.assertEqual(len(messages), 0)

            messages = Message.objects.filter(user=self.user)
            self.assertEqual(len(messages), 0)

            with freeze_time('2020-01-01'):
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 1)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 1)

            with freeze_time('2020-01-02'):
                # Create another, should be two
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 2)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 2)

            with freeze_time('2020-01-07'):
                # Create another, should be 3 because the min count saves it
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 3)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 3)

                # Creating another should keep it at 3 though because it will delete that oldest one now
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 3)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 3)

                # Creating 3 more should move it to 6 because the oldest is only 5 days old and there are only 6 total
                Message.objects.create(user=self.user, key='default', fail_silently=False)
                Message.objects.create(user=self.user, key='default', fail_silently=False)
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 6)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 6)

                # Creating another should keep it at 6 because max is 6 and there's no min age defined
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 6)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 6)

    def test_maintenance_max_age_min_count_max_count_with_message_id(self):

        INBOX_CONFIG = settings.INBOX_CONFIG.copy()
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_AGE'] = timezone.timedelta(days=5)
        INBOX_CONFIG['PER_USER_MESSAGES_MIN_COUNT'] = 3
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_COUNT'] = 6
        with self.settings(INBOX_CONFIG=INBOX_CONFIG):
            messages = Message.objects.filter(user=self.user).live()
            self.assertEqual(len(messages), 0)

            messages = Message.objects.filter(user=self.user)
            self.assertEqual(len(messages), 0)

            with freeze_time('2020-01-01'):
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 1)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 1)

            with freeze_time('2020-01-02'):
                # Create another, should be two
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 2)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 2)

            with freeze_time('2020-01-07'):
                # Create another, should be 3 because the min count saves it
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 3)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 3)

                # Creating another should keep it at 3 though because it will delete that oldest one now
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 3)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 4)

                # Creating 3 more should move it to 6 because the oldest is only 5 days old and there are only 6 total
                for i in range(3):
                    Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 6)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 7)

                # Creating another should keep it at 6 because max is 6 and there's no min age defined
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 6)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 8)

    def test_maintenance_max_age_min_count_max_count_min_age(self):

        INBOX_CONFIG = settings.INBOX_CONFIG.copy()
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_AGE'] = timezone.timedelta(days=5)
        INBOX_CONFIG['PER_USER_MESSAGES_MIN_COUNT'] = 3
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_COUNT'] = 6
        INBOX_CONFIG['PER_USER_MESSAGES_MIN_AGE'] = timezone.timedelta(days=3)
        with self.settings(INBOX_CONFIG=INBOX_CONFIG):
            messages = Message.objects.filter(user=self.user).live()
            self.assertEqual(len(messages), 0)

            messages = Message.objects.filter(user=self.user)
            self.assertEqual(len(messages), 0)

            with freeze_time('2020-01-01'):
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 1)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 1)

            with freeze_time('2020-01-05'):
                # Create another, should be two
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 2)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 2)

            with freeze_time('2020-01-07'):
                # Create another, should be 3 because the min count saves it
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 3)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 3)

                # Creating another should keep it at 3 though because it will delete that oldest one now
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 3)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 3)

                # Creating 3 more should move it to 6 because the oldest is only 2 days old and there are only 6 total
                Message.objects.create(user=self.user, key='default', fail_silently=False)
                Message.objects.create(user=self.user, key='default', fail_silently=False)
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 6)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 6)

                # Creating 1 more should move it to 7 because the oldest is only 2 days old and there is a min age
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 7)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 7)

                # Creating 1 more should add 1 more because the oldest is only 2 days old and there is a min age
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 8)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 8)

    def test_maintenance_max_age_min_count_max_count_min_age_with_message_id(self):

        INBOX_CONFIG = settings.INBOX_CONFIG.copy()
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_AGE'] = timezone.timedelta(days=5)
        INBOX_CONFIG['PER_USER_MESSAGES_MIN_COUNT'] = 3
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_COUNT'] = 6
        INBOX_CONFIG['PER_USER_MESSAGES_MIN_AGE'] = timezone.timedelta(days=3)
        with self.settings(INBOX_CONFIG=INBOX_CONFIG):
            messages = Message.objects.filter(user=self.user).live()
            self.assertEqual(len(messages), 0)

            messages = Message.objects.filter(user=self.user)
            self.assertEqual(len(messages), 0)

            with freeze_time('2020-01-01'):
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 1)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 1)

            with freeze_time('2020-01-05'):
                # Create another, should be two
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 2)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 2)

            with freeze_time('2020-01-07'):
                # Create another, should be 3 because the min count saves it
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 3)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 3)

                # Creating another should keep it at 3 though because it will delete that oldest one now
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 3)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 4)

                # Creating 3 more should move it to 6 because the oldest is only 2 days old and there are only 6 total
                for i in range(3):
                    Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 6)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 7)

                # Creating 1 more should move it to 7 because the oldest is only 2 days old and there is a min age
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 7)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 8)

                # Creating 1 more should add 1 more because the oldest is only 2 days old and there is a min age
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 8)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 9)

    def test_maintenance_max_age_max_count(self):

        INBOX_CONFIG = settings.INBOX_CONFIG.copy()
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_AGE'] = timezone.timedelta(days=5)
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_COUNT'] = 6
        with self.settings(INBOX_CONFIG=INBOX_CONFIG):
            messages = Message.objects.filter(user=self.user).live()
            self.assertEqual(len(messages), 0)

            messages = Message.objects.filter(user=self.user)
            self.assertEqual(len(messages), 0)

            with freeze_time('2020-01-01'):
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 1)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 1)

                # Creating 6 more should leave it at 6 because there is a max of 6
                for i in range(6):
                    Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 6)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 6)

            with freeze_time('2020-01-07'):
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 1)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 1)

    def test_maintenance_max_age_max_count_with_message_id(self):

        INBOX_CONFIG = settings.INBOX_CONFIG.copy()
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_AGE'] = timezone.timedelta(days=5)
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_COUNT'] = 6
        with self.settings(INBOX_CONFIG=INBOX_CONFIG):
            messages = Message.objects.filter(user=self.user).live()
            self.assertEqual(len(messages), 0)

            messages = Message.objects.filter(user=self.user)
            self.assertEqual(len(messages), 0)

            with freeze_time('2020-01-01'):
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 1)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 1)

                # Creating 6 more should leave it at 6 because there is a max of 6
                for i in range(6):
                    Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 6)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 7)

            with freeze_time('2020-01-07'):
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 1)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 8)

    def test_maintenance_max_age_max_count_min_age(self):

        INBOX_CONFIG = settings.INBOX_CONFIG.copy()
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_AGE'] = timezone.timedelta(days=5)
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_COUNT'] = 6
        INBOX_CONFIG['PER_USER_MESSAGES_MIN_AGE'] = timezone.timedelta(days=3)
        with self.settings(INBOX_CONFIG=INBOX_CONFIG):
            messages = Message.objects.filter(user=self.user).live()
            self.assertEqual(len(messages), 0)

            messages = Message.objects.filter(user=self.user)
            self.assertEqual(len(messages), 0)

            with freeze_time('2020-01-01'):
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 1)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 1)

                # Creating 6 more should be at 7 because of min age
                for i in range(6):
                    Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 7)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 7)

            with freeze_time('2020-01-05'):
                for i in range(3):
                    Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 6)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 6)

    def test_maintenance_max_age_max_count_min_age_with_message_id(self):

        INBOX_CONFIG = settings.INBOX_CONFIG.copy()
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_AGE'] = timezone.timedelta(days=5)
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_COUNT'] = 6
        INBOX_CONFIG['PER_USER_MESSAGES_MIN_AGE'] = timezone.timedelta(days=3)
        with self.settings(INBOX_CONFIG=INBOX_CONFIG):
            messages = Message.objects.filter(user=self.user).live()
            self.assertEqual(len(messages), 0)

            messages = Message.objects.filter(user=self.user)
            self.assertEqual(len(messages), 0)

            with freeze_time('2020-01-01'):
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 1)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 1)

                # Creating 6 more should be at 7 because of min age
                for i in range(6):
                    Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 7)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 7)

            with freeze_time('2020-01-05'):
                for i in range(3):
                    Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 6)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 10)

    def test_maintenance_max_count(self):

        INBOX_CONFIG = settings.INBOX_CONFIG.copy()
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_COUNT'] = 6
        with self.settings(INBOX_CONFIG=INBOX_CONFIG):
            messages = Message.objects.filter(user=self.user).live()
            self.assertEqual(len(messages), 0)

            messages = Message.objects.filter(user=self.user)
            self.assertEqual(len(messages), 0)

            with freeze_time('2020-01-01'):
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 1)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 1)

                # Creating 6 more should keep it at 6 because that's the max
                for i in range(6):
                    Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 6)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 6)

            with freeze_time('2020-02-01'):
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 6)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 6)

    def test_maintenance_max_count_with_message_id(self):

        INBOX_CONFIG = settings.INBOX_CONFIG.copy()
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_COUNT'] = 6
        with self.settings(INBOX_CONFIG=INBOX_CONFIG):
            messages = Message.objects.filter(user=self.user).live()
            self.assertEqual(len(messages), 0)

            messages = Message.objects.filter(user=self.user)
            self.assertEqual(len(messages), 0)

            with freeze_time('2020-01-01'):
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 1)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 1)

                # Creating 6 more should keep it at 6 because that's the max
                for i in range(6):
                    Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 6)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 7)

            with freeze_time('2020-02-01'):
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 6)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 8)

    def test_maintenance_max_count_min_age(self):

        INBOX_CONFIG = settings.INBOX_CONFIG.copy()
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_COUNT'] = 6
        INBOX_CONFIG['PER_USER_MESSAGES_MIN_AGE'] = timezone.timedelta(days=3)
        with self.settings(INBOX_CONFIG=INBOX_CONFIG):
            messages = Message.objects.filter(user=self.user).live()
            self.assertEqual(len(messages), 0)

            messages = Message.objects.filter(user=self.user)
            self.assertEqual(len(messages), 0)

            with freeze_time('2020-01-01'):
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 1)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 1)

                # Creating 6 more should go to 7 because of min age
                for i in range(6):
                    Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 7)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 7)

            with freeze_time('2020-01-04'):
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 8)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 8)

            with freeze_time('2020-01-05'):
                Message.objects.create(user=self.user, key='default', fail_silently=False)

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 6)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 6)

    def test_maintenance_max_count_min_age_with_message_id(self):

        INBOX_CONFIG = settings.INBOX_CONFIG.copy()
        INBOX_CONFIG['PER_USER_MESSAGES_MAX_COUNT'] = 6
        INBOX_CONFIG['PER_USER_MESSAGES_MIN_AGE'] = timezone.timedelta(days=3)
        with self.settings(INBOX_CONFIG=INBOX_CONFIG):
            messages = Message.objects.filter(user=self.user).live()
            self.assertEqual(len(messages), 0)

            messages = Message.objects.filter(user=self.user)
            self.assertEqual(len(messages), 0)

            with freeze_time('2020-01-01'):
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 1)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 1)

                # Creating 6 more should go to 7 because of min age
                for i in range(6):
                    Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 7)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 7)

            with freeze_time('2020-01-04'):
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 8)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 8)

            with freeze_time('2020-01-05'):
                Message.objects.create(user=self.user, key='default', fail_silently=False, message_id=uuid.uuid4())

                process_new_messages()
                process_new_message_logs()

                messages = Message.objects.filter(user=self.user).live()
                self.assertEqual(len(messages), 6)

                messages = Message.objects.filter(user=self.user)
                self.assertEqual(len(messages), 9)
