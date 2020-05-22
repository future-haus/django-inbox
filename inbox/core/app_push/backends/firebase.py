from typing import List
import logging

from firebase_admin._messaging_utils import UnregisteredError, ThirdPartyAuthError, SenderIdMismatchError, \
    QuotaExceededError

from inbox.constants import MessageLogStatus
from inbox.core.app_push.backends.base import BaseAppPushBackend
from inbox.core.app_push.message import AppPushMessage
import firebase_admin.messaging

logger = logging.getLogger(__name__)


class AppPushBackend(BaseAppPushBackend):

    _get_notification_key = None
    dry_run = False

    def __init__(self, fail_silently=False, dry_run=False):
        super().__init__(fail_silently=fail_silently)

        self.dry_run = dry_run

        try:
            self.firebase_app = firebase_admin.get_app()
        except ValueError:
            self.firebase_app = firebase_admin.initialize_app()

        self.messaging = firebase_admin.messaging

    def send_messages(self, messages: List[AppPushMessage]):

        for message in messages:

            if not message.entity.notification_key:
                continue

            if message.data is not None and isinstance(message.data, dict):
                data = {k: str(v) for k, v in message.data.items()}

            fcm_message = self.messaging.Message(
                notification=self.messaging.Notification(title=message.title, body=message.body),
                data=data,
                token=message.entity.notification_key
            )

            # TODO Handle failing silently if it is set to true
            try:
                resp = self.messaging.send(fcm_message, dry_run=self.dry_run)
                logger.info(resp)
            except UnregisteredError as msg:
                if message.message_log:
                    message.message_log.status = MessageLogStatus.FAILED
                    message.message_log.failure_reason = str(msg)
                    message.message_log.save()
                message.entity.clear_notification_key()
            except (QuotaExceededError,
                    SenderIdMismatchError,
                    ThirdPartyAuthError) as msg:
                if message.message_log:
                    message.message_log.status = MessageLogStatus.FAILED
                    message.message_log.failure_reason = str(msg)
                    message.message_log.save()
