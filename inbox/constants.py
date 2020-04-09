from django_enumfield import enum


class MessageMedium(enum.Enum):

    APP_PUSH = 0
    EMAIL = 1
    SMS = 2
    WEB_PUSH = 3

    __labels__ = {
        APP_PUSH: 'App Push',
        EMAIL: 'Email',
        SMS: 'SMS',
        WEB_PUSH: 'Web Push'
    }


class MessageLogStatus(enum.Enum):

    NEW = 0
    QUEUED = 1
    SENT = 2
    SKIPPED_FOR_PREF = 3
    FAILED = 4

    __labels__ = {
        NEW: 'New',
        QUEUED: 'Queued',
        SENT: 'Sent',
        SKIPPED_FOR_PREF: 'Skipped for preference',
        FAILED: 'Failed'
    }


class MessageLogFailureReason(enum.Enum):

    MISSING_TEMPLATE = 0
    INVALID_APP_PUSH_KEY = 1

    __labels__ = {
        MISSING_TEMPLATE: 'Missing template',
        INVALID_APP_PUSH_KEY: 'Invalid push key',
    }
