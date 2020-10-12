"""
Tools for sending app push.
"""
from typing import Dict

from django.conf import settings
from django.utils.module_loading import import_string

from inbox.core.app_push.message import AppPushMessage

__all__ = [
    'get_connection', 'send_message',
]


def get_connection(backend=None, fail_silently=False, **kwds):
    """Load an email backend and return an instance of it.

    If backend is None (default), use settings.EMAIL_BACKEND.

    Both fail_silently and other keyword arguments are used in the
    constructor of the backend.
    """
    klass = import_string(backend or settings.INBOX_CONFIG['BACKENDS']['APP_PUSH'])
    return klass(fail_silently=fail_silently, **kwds)


def send_message(entity, title, body: str = '', data: Dict = None, fail_silently=False, connection=None):
    """
    Easy wrapper for sending a single app push to a recipient list. All members
    of the recipient list will see the other recipients in the 'To' field.

    If auth_user is None, use the EMAIL_HOST_USER setting.
    If auth_password is None, use the EMAIL_HOST_PASSWORD setting.

    Note: The API for this method is frozen. New code wanting to extend the
    functionality should use the EmailMessage class directly.
    """
    connection = get_connection(fail_silently=fail_silently)
    message = AppPushMessage(entity, title, body, data, connection)

    return message.send()
