from typing import List

from django.conf import settings
from django.utils.module_loading import import_string
import firebase_admin
import firebase_admin.messaging

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
                token=self.notification_key(message),
            )
            # TODO Handle failing silently if it is set to true
            self.messaging.send(message)

    def notification_key(self, message: AppPushMessage):

        if not self._get_notification_key:
            try:
                self._get_notification_key = import_string(settings.INBOX_CONFIG.APP_PUSH_NOTIFICATION_KEY_GETTER)
            except ImportError:
                raise NotImplementedError('unable to load notification key getter')

        notification_key = self._get_notification_key(message)

        return notification_key
