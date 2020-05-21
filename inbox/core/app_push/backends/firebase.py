from typing import List

from django.conf import settings
from django.utils.module_loading import import_string
import firebase_admin
import firebase_admin.messaging

from inbox.constants import MessageLogStatus, MessageLogFailureReason
from inbox.core.app_push.backends.base import BaseAppPushBackend
from inbox.core.app_push.message import AppPushMessage


class AppPushBackend(BaseAppPushBackend):

    _get_notification_key = None

    def __init__(self, fail_silently=False):
        super().__init__(fail_silently=fail_silently)

        try:
            self.firebase_app = firebase_admin.get_app()
        except ValueError:
            self.firebase_app = firebase_admin.initialize_app()

        self.messaging = firebase_admin.messaging

    def send_messages(self, messages: List[AppPushMessage]):

        for message in messages:
            message = self.messaging.Message(
                notification=self.messaging.Notification(title=message.title, body=message.body),
                data=message.data,
                token=self.entity.notification_key,
            )

            # TODO Handle failing silently if it is set to true
            try:
                self.messaging.send(message)
            except firebase_admin.UnregisteredError:
                if message.message_log:
                    message.message_log.status = MessageLogStatus.FAILED
                    message.message_log.failure_reason = MessageLogFailureReason.INVALID_APP_PUSH_KEY
                    message.message_log.save()
                self.entity.clear_notification_key()
