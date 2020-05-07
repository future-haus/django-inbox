from inbox.constants import MessageMedium
from inbox.models import Message, MessageLog


def pre_message_log_save(message: Message, medium: MessageMedium, message_log: MessageLog):
    return None
