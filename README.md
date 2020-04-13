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

3. Configure INBOX_CONFIG in your Django settings file, here's the default:


    INBOX_CONFIG = {
        # Message groups are used to organize the messages and provide preferences and their defaults
        'MESSAGE_GROUPS': [
            {
                'id': 'DEFAULT',
                'label': 'News and Updates',
                'description': 'General news and updates.',  # Can be used in clients to describe what this preference is for
                'is_preference': True,  # Whether this is just used for grouping purposes (False) or also as a preference (True)
                'use_preference': None,  # If is_preference is False, this defines which group to use as preference
                'preference_defaults': {  # True/False or if you don't want that preference set to None
                    'APP_PUSH': True,
                    'EMAIL': True,
                    'SMS': True,
                    'WEB_PUSH': True
                },
                'message_keys': []  # List of message keys that fall into this group
            }
        ],
    }

4. Run `python manage.py migrate` to create the polls models.

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
* `inbox_{message_key}_subject.txt`
* `inbox_{message_key}_body.html`

For the subject:
* `inbox_{message_key}_subject_{'app_push'|'email'}.txt`

For the body:
* `inbox_{message_key}_body_{'app_push'}.txt`
* `inbox_{message_key}_body_{'email'}.html`

Templates also determine what mediums are sent to, if a template doesn't exist for a medium, that medium won't be used.
Each template receives the following data: user, link, data that were used when creating the `Message`

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
