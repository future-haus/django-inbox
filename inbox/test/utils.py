import os
import codecs

from inbox import settings as inbox_settings
from inbox.core import app_push


INBOX_SETTINGS = inbox_settings.get_config()


def dump_template(filename, content):
    full_filename = os.path.join(INBOX_SETTINGS['TESTING_MEDIUM_OUTPUT_PATH'], filename)

    if not os.path.exists(os.path.dirname(full_filename)):
        try:
            os.makedirs(os.path.dirname(full_filename))
        except:
            pass

    with codecs.open(full_filename, 'w', encoding='utf8') as fp:
        fp.write(content)


class AppPushTestCaseMixin:

    def setUp(self):
        app_push.outbox = []
        super().setUp()

    def tearDown(self):
        app_push.outbox = []
        super().tearDown()
