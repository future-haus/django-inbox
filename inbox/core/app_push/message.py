from django.contrib.auth import get_user_model

User = get_user_model()


class AppPushMessage:

    message_log = None

    def __init__(self, entity: User, title=None, body=None, data=None, message_log=None, connection=None):
        self.entity = entity
        self.title = title
        self.body = body
        self.data = data or {}
        self.message_log = message_log
        self.connection = connection

    def get_connection(self, fail_silently=False):
        from inbox.core.app_push import get_connection
        if not self.connection:
            self.connection = get_connection(fail_silently=fail_silently)
        return self.connection

    def send(self, fail_silently=False):
        return self.get_connection(fail_silently).send_messages([self])
