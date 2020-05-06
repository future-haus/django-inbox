from inbox.constants import MessageMedium
from inbox.models import Message, MessageLog


def pre_message_log_save(message: Message, medium: MessageMedium, message_log: MessageLog):
    return None


def post_message_to_logs(message: Message):

    if message.logs.count() <= 0:
        Message.objects.create(user=message.user, key=message.key)

    return message
