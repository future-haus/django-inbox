import json
from typing import List
import logging

from django.conf import settings
from firebase_admin._messaging_utils import UnregisteredError, ThirdPartyAuthError, SenderIdMismatchError, \
    QuotaExceededError

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

        self.fcm = FCMNotification(
            api_key=settings.INBOX_CONFIG['BACKENDS']['APP_PUSH_CONFIG']['GOOGLE_FCM_SENDER_KEY']
        )

    def send_messages(self, messages: List[AppPushMessage]):

        for message in messages:

            if not message.entity.notification_key:
                continue

            if message.data is not None and isinstance(message.data, dict):
                data = {k: str(v) for k, v in message.data.items()}

            try:
                content_available = message.title is None and message.body is None
                response = self.fcm.notify_single_device(registration_id=message.entity.notification_key,
                                                         message_title=message.title,
                                                         message_body=message.body,
                                                         data_message=data,
                                                         content_available=content_available)
            except Exception as msg:
                if message.message_log:
                    message.message_log.status = MessageLogStatus.FAILED
                    message.message_log.failure_reason = str(msg)
                    logger.warning('Exception when calling notify_single_device for {}'.format(
                        message.entity.notification_key
                    ))
                    logger.warning(msg)
                    message.message_log.save()

            if response['failure'] > 0:
                if 'failed_registration_ids' in response:
                    failed_registration_ids = []
                    for registration_id in response['failed_registration_ids']:
                        failed_registration_ids.append(registration_id)

                    msg = ', '.join(failed_registration_ids)
                    logger.warning('Failed registration IDs: {}'.format(msg))
                else:
                    errors = []
                    for result in response['results']:
                        errors.append(result['error'])

                    msg = "\n".join(errors)
                    logger.warning('FCM failure: {}'.format(msg))
            else:
                logger.info('FCM success')
                logger.info(json.dumps(response))
