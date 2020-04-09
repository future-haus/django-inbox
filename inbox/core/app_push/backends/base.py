from django.contrib.auth import get_user_model

User = get_user_model()


class BaseAppPushBackend:
    """
    Base class for app push backend implementations.

    Subclasses must at least overwrite send_messages().
    """
    def __init__(self, fail_silently=False, **kwargs):
        self.fail_silently = fail_silently

    def send_messages(self, email_messages):
        """
        Send one or more AppPushMessage objects and return the number of app push
        messages sent.
        """
        raise NotImplementedError('subclasses of BaseAppPushBackend must override send_messages() method')


