from django.db import transaction
from django.utils import timezone

from inbox.constants import MessageLogStatus
from inbox.models import MessageLog


def process_new_messages():

    message_logs = MessageLog.objects \
                       .select_related('message', 'message__user') \
                       .select_for_update(skip_locked=True).filter(send_at__lte=timezone.now(),
                                                                   status=MessageLogStatus.NEW)[:25]

    with transaction.atomic():
        for message_log in message_logs:
            if message_log.can_send:
                message_log.status = MessageLogStatus.SENT
                message_log.send()
            else:
                message_log.status = MessageLogStatus.SKIPPED_FOR_PREF

            message_log.save()
