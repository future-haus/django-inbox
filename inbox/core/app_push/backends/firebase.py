import json
from typing import List
import logging

from inbox import settings as inbox_settings
from inbox.constants import MessageLogStatus
from inbox.core.app_push.backends.base import BaseAppPushBackend
from inbox.core.app_push.message import AppPushMessage
from pyfcm import FCMNotification

logger = logging.getLogger(__name__)


class AppPushBackend(BaseAppPushBackend):

    _get_notification_key = None
    dry_run = False

    def __init__(self, fail_silently=False, dry_run=False):
        super().__init__(fail_silently=fail_silently)

        self.dry_run = dry_run

        settings = inbox_settings.get_config()["BACKENDS"]["APP_PUSH_CONFIG"]
        service_account_file = settings.get("SERVICE_ACCOUNT_FILE")
        credentials = settings.get("CREDENTIALS")
        project_id = settings.get("PROJECT_ID")

        self.fcm = FCMNotification(
            service_account_file=service_account_file,
            credentials=credentials,
            project_id=project_id,
        )

    def send_messages(self, messages: List[AppPushMessage]):

        for message in messages:

            if not message.entity.notification_key:
                continue

            if message.data is not None and isinstance(message.data, dict):
                data = {k: str(v) for k, v in message.data.items()}

            try:
                content_available = message.title is None and message.body is None
                apns_config = (
                    {
                        "payload": {
                            "aps": {
                                "content-available": 1,
                            }
                        }
                    }
                    if content_available
                    else None
                )
                response = self.fcm.notify(
                    fcm_token=message.entity.notification_key,
                    notification_title=message.title,
                    notification_body=message.body,
                    data_payload=data,
                    apns_config=apns_config,
                )
            except Exception as msg:
                if message.message_log:
                    message.message_log.status = MessageLogStatus.FAILED
                    message.message_log.failure_reason = str(msg)
                    message.message_log.save()
                logger.warning(msg)
                logger.warning(
                    "Exception when calling notify for {}".format(
                        message.entity.notification_key
                    )
                )
            else:
                logger.info("FCM success: %s", json.dumps(response))
