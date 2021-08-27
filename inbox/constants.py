from functools import lru_cache

from django_enumfield import enum


class MessageMedium(enum.Enum):

    APP_PUSH = 1
    EMAIL = 2
    SMS = 3
    WEB_PUSH = 4

    __labels__ = {
        APP_PUSH: 'App Push',
        EMAIL: 'Email',
        SMS: 'SMS',
        WEB_PUSH: 'Web Push'
    }

    @classmethod
    @lru_cache(maxsize=None)
    def keys(cls):
        return [item[0].lower() for item in cls.items()]


class MessageLogStatus(enum.Enum):

    NEW = 1
    QUEUED = 2
    SENT = 3
    SKIPPED_FOR_PREF = 4
    FAILED = 5

    __labels__ = {
        NEW: 'New',
        QUEUED: 'Queued',
        SENT: 'Sent',
        SKIPPED_FOR_PREF: 'Skipped for preference',
        FAILED: 'Failed'
    }


class MessageLogFailureReason(enum.Enum):

    MISSING_TEMPLATE = 101
    MISSING_APP_PUSH_KEY = 102

    EMAIL_NOT_VERIFIED = 201
    SMS_NOT_VERIFIED = 202

    UNKNOWN_EXCEPTION = 301

    __labels__ = {
        MISSING_TEMPLATE: 'Missing template',
        MISSING_APP_PUSH_KEY: 'Missing App Push Key',

        EMAIL_NOT_VERIFIED: 'Email is not verified',
        SMS_NOT_VERIFIED: 'SMS is not verified',

        UNKNOWN_EXCEPTION: 'Unknown Exception'
    }
