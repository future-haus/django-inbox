import os

from inbox import settings as inbox_settings
from inbox.constants import MessageMedium
from inbox.core import app_push
from inbox.models import MessageLog, Message
from inbox.utils import process_new_messages, process_new_message_logs


INBOX_SETTINGS = inbox_settings.get_config()


def dump_template(filename, content):
    full_filename = os.path.join(INBOX_SETTINGS['TESTING_MEDIUM_OUTPUT_PATH'], filename)

    if not os.path.exists(os.path.dirname(full_filename)):
        try:
            os.makedirs(os.path.dirname(full_filename))
        except:
            pass

    with open(full_filename, 'w', encoding='utf8') as fp:
        fp.write(content)


class InboxTestCaseMixin:

    message_key = ''

    def setUp(self):
        app_push.outbox = []
        super().setUp()

    def tearDown(self):
        app_push.outbox = []
        super().tearDown()

    def assert_message_count_for(self, user, count):
        messages = Message.objects.filter(user=user, key__in=[self.message_key])
        self.assertEqual(len(messages), count)

    def assert_email_message_log_count_for(self, user, count):
        message_logs = MessageLog.objects \
            .filter(message__user=user, message__key__in=[self.message_key]) \
            .filter(medium=MessageMedium.EMAIL)

        self.assertEqual(len(message_logs), count)

    def assert_app_push_message_log_count_for(self, user, count):

        message_logs = MessageLog.objects\
            .filter(message__user=user, message__key__in=[self.message_key])\
            .filter(medium=MessageMedium.APP_PUSH)

        self.assertEqual(len(message_logs), count)

    def process_inbox(self):
        process_new_messages()
        process_new_message_logs()
