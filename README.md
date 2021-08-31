Inbox
=====

Inbox is a Django app to store messages for users. For each
message, various notifications can be sent out through other
channels like app push notifications, email.

Future channels: SMS, Web push

Quick start
-----------

1. Add "inbox" to your INSTALLED_APPS setting like this

    INSTALLED_APPS = [
        ...
        'inbox',
    ]

2. Include any desired pre-built views in your API, or build your own

3. Configure INBOX_CONFIG in your Django settings file, example:

```python
INBOX_CONFIG = {
    # Message groups are used to organize the messages and provide preferences and their defaults
    'MESSAGE_GROUPS': [
        {
            'id': 'default',
            'label': 'News and Updates',
            'description': 'General news and updates.',  # Can be used in clients to describe what this preference is for
            'is_preference': True,  # Whether this is just used for grouping purposes (False) or also as a preference (True)
            'use_preference': None,  # If is_preference is False, this defines which group to use as preference
            'data': {},  # Arbitrary data block that is return on Message objects and available in templates as data_group
            'preference_defaults': {  # True/False or if you don't want that preference set to None
                'app_push': True,
                'email': True,
                'sms': None,
                'web_push': None
            },
            'message_keys': []  # List of message keys that fall into this group
            'skip_app_push': [],  # List of message keys to skip for associated medium
            'skip_email': [],
            'skip_web_push': [],
            'skip_sms': []
        }
    ],
    'BACKENDS': {
        'APP_PUSH': 'inbox.core.app_push.backends.firebase.AppPushBackend',
        'APP_PUSH_CONFIG': {  # Config specific to the app push backend being used
            'GOOGLE_FCM_SERVER_KEY': 'abc'
        }
    },
    'CHECK_IS_EMAIL_VERIFIED': True,  # Calls a method on the User being sent to verify the email is verified before sending.
    'CHECK_IS_SMS_VERIFIED': True,  # Calls a method on the User being sent to verify the SMS number is verified before sending.
    'TESTING_MEDIUM_OUTPUT_PATH': None,  # Only set this in the testing environment, it will write final outputs for mediums being sent to.
    'DISABLE_NEW_DATA_SILENT_APP_PUSH': False,  # If you have groups with app_push and don't want the silent data push to go out, set this to True
    'MESSAGE_CREATE_FAIL_SILENTLY': True,  # Fail silently if the properties passed to Message.create() would cause an error, this is useful for not crashing in production
    'HOOKS_MODULE': None  # Supports post_message_get, pre_message_log_save, post_message_log_save, and post_message_to_logs
    'PROCESS_NEW_MESSAGES_LIMIT': 25,  # Default limit for processing new messages
    'PROCESS_NEW_MESSAGE_LOGS_LIMIT': 25,  # Default limit for processing new message logs
    'PER_USER_MESSAGES_MAX_AGE': None,  # timedelta, Maximum age of a message for when it's available for maintenance cleanup
    'PER_USER_MESSAGES_MIN_COUNT': None,  # integer, Used to bound max age if desired, only has an effect if max age is set
    'PER_USER_MESSAGES_MAX_COUNT': None,  # integer, Maximum count used, when messages exceed this they are available for maintenance cleanup
    'PER_USER_MESSAGES_MIN_AGE': None,  # timedelta, Used to bound max count, if desired, only has an effect if max count is set
    'MAX_AGE_BEYOND_SEND_AT': None,  # timedelta, Used to control the furthest out you can get from a send_at before the Message won't be sent at all, safe-guard
}
```

Setting a `preference_default` medium to `None` disables it from being returned in the API or used as an option. Setting 
it to `False` means you want the UI to present it as "off" by default.

The `PER_USER_MESSAGES_*` are used to control the growth of the Inbox Message and MessageLog. If your usage is one
where a `User` viewing old Messages is unlikely, or not useful even if they can, then you may want to set limits to how
long, or how many, are kept around. When setting the `PER_USER_MESSAGES_*` settings you don't have to use all four 
settings, you can use any of the following combinations:

- max_age
- max_age + min_count
- max_age + min_count + max_count
- max_age + min_count + max_count + min_age
- max_age + max_count
- max_age + max_count + min_age
- max_count
- max_count + min_age

You can also leave them as None and no maintenance cleanup is ever done, retaining messages indefinitely. If a Message
has a set message_id, it is left but marked as deleted so as to not show to the user and match the behavior
of the other messages that are removed but left intact incase the message id is also being used as de-duplication.

You can leave off `is_preference`, `use_preference`, and `preference_defaults` if you're good with the above defaults. 
The above example could look like this and get the same result:

```python
INBOX_CONFIG = {
    # Message groups are used to organize the messages and provide preferences and their defaults
    'MESSAGE_GROUPS': [
        {
            'id': 'default',
            'label': 'News and Updates',
            'description': 'General news and updates.',  # Can be used in clients to describe what this preference is for
            'message_keys': []  # List of message keys that fall into this group
        }
    ],
}
```

4. Run `python manage.py migrate` to create the inbox models.

There are a few property getters that are required to be on your `User` depending on the mediums in use:

- app_push: `notification_key`
- email: `is_email_verified`
- sms: `is_sms_verified`

Concepts
========

#### Intro

This push notification medium includes a Firebase backend for sending and only supports the device grouping method to
send to which uses the `notification_key` generated by adding `registration_token`s to a device group for a given
`notification_key_name`. If there's every a desire to send to a specific `registration_token` 
(ie single physical device) we'll need to add in additional API endpoints and expand the send_messages method to handle
that. I don't forsee us needing to do this for any reason which is why it isn't included currently.

#### Message Groups

Message groups are used to define broader groups of specific messages that go out primarily to define user preferences
on whether they do or don't want to receive messages within that group. For example you may have a message group id
of 'FRIENDS' and that controls how and if a user would get notifications sent to them when a message within that group
is created. There should always be a `MESSAGE_GROUP` with an id of `default`, that is the one that will be used as the
fallback in certain cases where things aren't configured either intentionally or unintentionally.

#### Message Keys

These are the identifiers for the specific message content being sent out. For example, if
you needed to send an email/app push with the subject of "You have a new friend request!", that might have a key of
`new_friend_request`, this defines what templates django-inbox will look for to send out to the various mediums. If
a message key is not present in any `MESSAGE_GROUP` config an error will be raised.

#### Template Naming Convention

For the subject and body in the inbox:

* `inbox/{message_key}/subject.txt`
* `inbox/{message_key}/body.html`

Optionally for the inbox you can include a `body_excerpt.html` or `body_excerpt.txt` that will be used for the body when
returned in the list endpoint, and stored in the body field in the DB. For the retrieve endpoint it will still use the
full `body.html` or `body.txt` and loaded of the disk as needed rather than being stored. Better for long form content.

For the subject:

* `inbox/{message_key}/subject_{'app_push'|'email'}.txt`

For the body:

* `inbox/{message_key}/body_{'app_push'}.txt`
* `inbox/{message_key}/body_{'email'}.html`

Templates also determine what mediums are sent to, if a template doesn't exist for a medium, that medium won't be used.
Each template receives the following context: `user`, `data` (email and inbox also receive `data_email`) that were 
used when creating the `Message`.

#### [Endpoints/Views](#markdown-header-endpointsviews)

There are some views provided for easy implementation of the library without building your own, just add them to your routing config in urls.py.

* `GET /api/v1/users/{userId}/messages` - Get paginated list of messages for a `User`, most recent first
* `POST /api/v1/users/{userId}/messages/read` - Mark all messages as read for a `User`
* `GET /api/v1/users/{userId}/messages/unread-count` - Get unread count for a `User`
* `GET /api/v1/messages/{messageId}` - Get message
* `PUT /api/v1/messages/{messageId}` - Update message, used to set `is_read` to `true` or `false`
* `DELETE /api/v1/messages/{messageId}` - Delete a message, no longer returned in list call.

Example routing setup:

    urls.py
    
    router = ExtendedSimpleRouter(trailing_slash=False)
    users_router = router.register(r'users', UserViewSet)
    users_router.register(r'messages', MessageViewSet, basename='users_messages', parents_query_lookups=['user'])
    messages_router = router.register(r'messages', MessageViewSet, basename='messages')

User message preferences mixin endpoints:

* `GET /api/v1/users/{userId}/message-preferences` - Get message preferences for a `User`.
* `PUT /api/v1/users/{userId}/message-preferences` - Update all `MessagePreferences` for a `User` at once, same 
payload that `GET` returns.
* `PUT /api/v1/users/{userId}/message-preferences/{messagePreferenceId}/{medium:'app_push'|'email'}` - Update 
individual MessagePreference+medium combo, this endpoint is suggested if the implementation is saving each 
MessagePreference individually as the `User` toggles it to avoid race conditions the whole payload endpoint would
introduce. The payload is just a boolean `true` or `false`.

Add `NestedMessagePreferencesMixin` into your `UserViewSet`:

```python
class UserViewSet(NestedMessagePreferencesMixin, mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    ...
```

Operate on MessagePreferences while not logged in, useful for getting/updating from links in emails, or other 
message mediums.

* `GET /api/v1/message_preferences/{token}` operates the same as `GET /api/v1/users/{userId}/message_preferences`
* `PUT /api/v1/message_preferences/{token}` operates the same as `PUT /api/v1/users/{userId}/message_preferences`
* `PUT /api/v1/message_preferences/{token}/{messagePreferenceId}/{medium:'app_push'|'email'}` operates the same as
`PUT /api/v1/users/{userId}/message_preferences/{messagePreferenceId}/{medium:'app_push'|'email'}`

#### Usage

Simple:

```python
Message.objects.create(user=user, key='example_message_key')
```

Use a message_id if you need to be able to track whether you've sent a message before (eg did we send this user their
morning reminder to drink coffee on Mon, Aug 8, 2010?). A message id is only unique to a user, no need to interpolate
user_id into the message_id to enforce uniqueness across users. They should really only be used if you're unable
to determine whether a message was sent from the message key, date sent, user, etc alone. The primary purposes is to
prevent duplicate messages from being created and it's the only way you're able to accomplish that reasonably. If you're
also wanting to take advantage of message maintenace feature using the `PER_USER_MESSAGES_*` settings, any
`Message` that has a message_id is not removed and is left, thereby not clearing up space.

```python
Message.objects.create(user=user, key='morning_coffee_reminder', message_id=f'mcr_20100808')
```

If you want to force a test send of a Message that will bypass any hooks and other logic like
message preferences, then set the `is_forced=True` property on the Message.
```python
Message.objects.create(user=user, key='example_message_key', is_forced=True)
```

Determine whether a message id (or list of a message ids) have Messages.

```python
existing_message_ids, missing_message_ids = Message.objects.exists(msg_id_1)
```

```python
existing_message_ids, missing_message_ids = Message.objects.exists([msg_id_1, msg_id_2])
```

Signals
=======

`unread_count`

Fires when number of unread messages changes. Receives one parameter, `count`, the number of
unread messages.

`message_preferences_changes`

Fires when any message preference group medium changes. Receives `delta` which is structured
just like message preferences and contains only the groups that contained changes and only
the mediums that changed with their new/current value.

    

Test
====

Setup Postgres database to run tests.

    CREATE ROLE inbox WITH LOGIN PASSWORD 'password';
    ALTER USER inbox WITH superuser;
    CREATE DATABASE inbox;
    ALTER ROLE inbox SET client_encoding TO 'utf8';
    ALTER ROLE inbox SET default_transaction_isolation TO 'read committed';
    ALTER ROLE inbox SET timezone TO 'UTC';
    ALTER USER inbox CREATEDB;
    GRANT ALL PRIVILEGES ON DATABASE inbox TO inbox;

Build and Upload
================

Make sure you have twine in your system Python. Bump the version number in setup.py, major, minor, patch (semver). Commit
to repo and then run:

`python setup.py sdist bdist_wheel upload`

TODOs
=====

https://3.basecamp.com/4413376/projects/16662219
