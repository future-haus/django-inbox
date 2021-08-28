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
    NOT_SENDABLE = 4
    FAILED = 5

    __labels__ = {
        NEW: 'New',
        QUEUED: 'Queued',
        SENT: 'Sent',
        NOT_SENDABLE: 'Not Sendable',
        FAILED: 'Failed',
    }


class MessageLogStatusReason(enum.Enum):

    MISSING_TEMPLATE = 101
    MISSING_ID = 102

    NOT_VERIFIED = 201

    PREFERENCE_OFF = 301

    __labels__ = {
        MISSING_TEMPLATE: 'Missing template',
        MISSING_ID: 'Missing id',

        NOT_VERIFIED: 'Not verified',

        PREFERENCE_OFF: 'Pref off'
    }
