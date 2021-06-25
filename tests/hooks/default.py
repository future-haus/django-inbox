from inbox import settings as inbox_settings
from inbox.constants import MessageLogStatus, MessageMedium, MessageLogFailureReason
from inbox.models import MessageLog


def can_send(message_log: MessageLog):
    user = message_log.message.user
    message_group = message_log.message.group

    if message_log.medium == MessageMedium.APP_PUSH:
        if not user.notification_key:
            message_log.status = MessageLogStatus.FAILED
            message_log.failure_reason = MessageLogFailureReason.MISSING_APP_PUSH_KEY
            return False

    if message_log.medium == MessageMedium.EMAIL:
        if inbox_settings.get_config()['CHECK_IS_EMAIL_VERIFIED'] and not user.is_email_verified:
            message_log.status = MessageLogStatus.FAILED
            message_log.failure_reason = MessageLogFailureReason.EMAIL_NOT_VERIFIED
            return False

    if message_log.medium == MessageMedium.SMS:
        if inbox_settings.get_config()['CHECK_IS_SMS_VERIFIED'] and not user.is_sms_verified:
            message_log.status = MessageLogStatus.FAILED
            message_log.failure_reason = MessageLogFailureReason.SMS_NOT_VERIFIED
            return False

    preference = next((g for g in user.message_preferences.groups if g['id'] == message_group['id']))

    if preference.get(message_log.medium.name.lower()):
        return True
    else:
        message_log.status = MessageLogStatus.SKIPPED_FOR_PREF

    return False
