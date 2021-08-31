from inbox import settings as inbox_settings
from inbox.constants import MessageLogStatus, MessageMedium, MessageLogStatusReason
from inbox.models import MessageLog


def can_send(message_log: MessageLog):
    user = message_log.message.user

    if message_log.medium == MessageMedium.APP_PUSH:
        if not user.notification_key:
            message_log.status = MessageLogStatus.NOT_SENDABLE
            message_log.status_reason = MessageLogStatusReason.MISSING_ID
            return False

    if message_log.medium == MessageMedium.EMAIL:
        if inbox_settings.get_config()['CHECK_IS_EMAIL_VERIFIED'] and not user.is_email_verified:
            message_log.status = MessageLogStatus.NOT_SENDABLE
            message_log.status_reason = MessageLogStatusReason.NOT_VERIFIED
            return False

    if message_log.medium == MessageMedium.SMS:
        if inbox_settings.get_config()['CHECK_IS_SMS_VERIFIED'] and not user.is_sms_verified:
            message_log.status = MessageLogStatus.NOT_SENDABLE
            message_log.status_reason = MessageLogStatusReason.NOT_VERIFIED
            return False

    if not message_log.is_send_at_in_range:
        return False

    if not message_log.is_preferred:
        return False

    return True
