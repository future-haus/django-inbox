from inbox.core import app_push
from inbox.core.app_push.backends.base import BaseAppPushBackend


class AppPushBackend(BaseAppPushBackend):
    """
    An app push backend for use during test sessions.

    The test connection stores app push messages in a dummy outbox,
    rather than sending them out on the wire.

    The dummy outbox is accessible through the outbox instance attribute.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(app_push, 'outbox'):
            app_push.outbox = []

    def send_messages(self, messages):
        """Redirect messages to the dummy outbox"""
        msg_count = 0
        for message in messages:  # .message() triggers header validation

            if not message.entity.notification_key:
                continue

            app_push.outbox.append(message)
            msg_count += 1
        return msg_count
