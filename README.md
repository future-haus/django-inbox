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
            'preference_defaults': {  # True/False or if you don't want that preference set to None
                'app_push': True,
                'email': True,
                'sms': None,
                'web_push': None
            },
            'message_keys': []  # List of message keys that fall into this group
        }
    ],
    'APP_PUSH_NOTIFICATION_KEY_GETTER': None,  # Point to a method that gets the user and needs to return the notification key if sending push
    'BACKENDS': {
        'APP_PUSH': 'inbox.core.app_push.backends.firebase.AppPushBackend'
    },
    'TESTING_MEDIUM_OUTPUT_PATH': None  # Only set this in the testing environment, it will write final outputs for mediums being sent to.
}
```

Setting a `preference_default` medium to `None` disables it from being returned in the API or used as an option. Setting 
it to `False` means you want the UI to present it as "off" by default.

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

For the subject:

* `inbox/{message_key}/subject_{'app_push'|'email'}.txt`

For the body:

* `inbox/{message_key}/body_{'app_push'}.txt`
* `inbox/{message_key}/body_{'email'}.html`

Templates also determine what mediums are sent to, if a template doesn't exist for a medium, that medium won't be used.
Each template receives the following context: `user`, `data` (email and inbox also receive `data_email`) that were 
used when creating the `Message`.

#### Endpoints/Views

There are some views provided for easy implementation of the library without building your own, just add them to your routing config in urls.py.

* `GET /api/v1/users/{userId}/messages` - Get paginated list of messages for a user, most recent first
* `POST /api/v1/users/{userId}/messages/read` - Mark all messages as read for a user
* `GET /api/v1/messages/{messageId}` - Get message
* `PUT /api/v1/messages/{messageId}` - Update message, used to set `is_read` to `true` or `false`
* `DELETE /api/v1/messages/{messageId}` - Delete a message, no longer returned in list call.

Example routing setup:

    urls.py
    
    router = ExtendedSimpleRouter(trailing_slash=False)
    users_router = router.register(r'users', UserViewSet)
    users_router.register(r'messages', MessageViewSet, basename='users_messages', parents_query_lookups=['user'])
    messages_router = router.register(r'messages', MessageViewSet, basename='messages')
    

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
