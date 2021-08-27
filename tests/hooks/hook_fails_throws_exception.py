from inbox.models import MessageLog


def can_send(message_log: MessageLog):
    print(message_log.missing_prop)
