# Releases

#### 0.8.10 (2022-06-10)

Improvement

- Add index on Message for send_at field ordered ascending. In the process new messages function, it specifies pulling ordered by send at, which will use this new index.
- Add multi-column index on MessageLog for send_at and status to improve performance. Add order_by to query on processing new message logs.

#### 0.8.9 (2022-06-10)

Changes

- Add updated_at property to the MessageLog model.

#### 0.8.8 (2021-10-25)

Changes

- Pass the User object to existing signals as the `user` parameter.

#### 0.8.7 (2021-08-31)

Improvement

- Add ability to specify a max age that the current time can surpass the send_at on
  a Message before it's considered too old to send. The primary use case is a safe-guard
  if the system or cron was not operational for any reason and Messages are
  time-sensitive they won't be sent.

#### 0.8.6 (2021-08-28)

Changes

- Rename MessageLog.failure_reason to MessageLog.status_reason
- Remove MessageLogStatus.SKIPPED_FOR_PREF, replace with MessageLogStatus.NOT_SENDABLE
  that will be used for a few different scenarios where a Message can't
  be sent but isn't really a "failure", just a non-sendable situation like
  an unverified medium ID (email, sms, push), or pref off for that message group, etc.
- Rename MessageLogFailureReason to MessageLogStatusReason
- Update values under MessageLogStatusReason to be a bit more generic, like
  collapsing EMAIL_NOT_VERIFIED and SMS_NOT_VERIFIED into NOT_VERIFIED since
  each MessageLog is only tied to one Medium.
- When a message can't be sent because it fails `can_send` the status is
  set to NOT_SENDABLE so that it's no longer picked up in processing on the next
  loop. Previously its status could be left as NEW, so it'd just be reprocessed
  (and skipped) the next time as well.

#### 0.8.5 (2021-08-27)

Improvements

- Catch exceptions when determing to send (can_send) and performing the send so it doesn't hold up other
message logs being processed. They are logged as a failure, failure reason is the str
  representation of the exception.


#### 0.8.4 (2021-07-29)

Improvements

- Send X-MC-Tags, X-SMTPAPI, and X-Mailgun-Tag headers with the message.key when sending an email to allow
categorizating tracking in those platforms.

#### 0.8.3 (2021-06-28)

Improvements

- Ability to specify hooks for overriding the `can_send` method and portions thereof using `can_send_{medium}` for 
  specific message keys. Ex: Create a method in the message key's hook file called
  `can_send` or `can_send_email` and return a boolean on whether the message should
  be allowed to be sent.

#### 0.8.2 (2021-03-25)

Improvements

- Previous index improvement was applied in wrong order causing one of the
  new index to not even be created.

#### 0.8.1 (2021-03-24)

Improvements

- Optimizing indexes for send_at on the message table

#### 0.8.0 (2021-02-25)

Changes

- Changes for Django deprecations that are upcoming
- For Django 3.1 and newer use the new generic JSONField

#### 0.7.4 (2021-01-14)

Fixes

- Add extras option during install to specify `admin_commands` that will install dependencies needed
  to support the admin commands included but aren't necessary in production environments.
  `pip install django-inbox[admin_commands]`

#### 0.7.3 (2021-01-12)

Fixes

- Fixes a few spots where we were incorrectly referencing settings values directly instead of 
  through config helper that loads defaults merged with project settings.

#### 0.7.2 (2020-12-29)

Changes

- Bump requirement on Django to include 3.1

#### 0.7.1 (2020-12-28)

Fixes

- Broken error message when missing a template in a particular case.

#### 0.7.0 (2020-12-10)

Improvements

- Unify around single TestCaseMixin for Inbox related asserts and setup/teardown of app push outbox.
If you're using the older AppPushTestCaseMixin you should transition to the new one.

Fixes

- Writing of templates when running template output in testing would fail under Windows, this has been resolved.

#### 0.6.1 (2020-11-29)

Improvements

- Remove index on Message.body because this will generally be a large amount of text and if you want to search it
the more correct approach would be to use full text indexing or a separate search engine. With the index in place,
the field was limited based on the database engine being used and it's max size for indexing.

#### 0.6.0 (2020-10-14)

Features

- Add configuration to perform maintenance of deleting older user messages based on min/max count per user and/or
age of message. If a message has a message_id, which many times is used to prevent future messages of the same
being sent then they are left and hidden from the user.

#### 0.5.1 (2020-10-14)

Improvements

- No longer use uuid4 as default value when message_id isn't specified for a Message. New default is `NULL`
allowing you to clearly distinguish Messages that had message_id intentionally set vs not.
=======

#### 0.5.0 (2020-10-12)

Features

- Add signal, `message_preferences_changed`, that fires when one or more mediums on any `MessagePreference` group 
changes value.

Improvements

- When creating a Message, validation error order has changed so that if it's not found in any group
it throws that error first, then template missing error. These errors are only thrown if fail silently is off.

#### 0.4.1 (2020-10-07)

Improvement

- Setting `is_forced=True` on a new Message will now override message_id so that uniqueness isn't taken into account
allowing the Message to always be created.

Fixes

- Fix issue where if you pass `send_at=None` on Message.objects.create it would fail when it should just default
to using timezone.now

#### 0.4.0 (2020-10-06)

Features

- Add ability to GET/PUT to message_preferences with an token that can be sent along in any `Message` but specifically
design for the needs/requirements of email.
- Ability to set body_excerpt.html or body_excerpt.txt templates for a message so that the body stored in the database
for a Message can be shorter for list calls and then individual endpoint return full template from disk, useful for
long form content. If you want long form stored in DB just don't include those new templates.
- Ability to force send a Message, bypasses hooks which could cancel it and bypasses checks like verified email or
if that message group preference is off it will still send.

#### 0.3.38 (2020-09-09)

Improvement

- Adds ability to pass force=True to Message.delete method so that you can force an actual deletion rather than a
tombstoning.

#### 0.3.37 (2020-09-08)

Improvement

- Adds 'post_message_get' callback that is ran before any message log initialization or hooks are ran when processing
message logs. Useful for altering or removing the Message object itself. If None is returned from hook then rest of
processing for that Message is skipped, otherwise return the Message.

#### 0.3.36 (2020-09-02)

Fixes

- When adding new preferences, if a user doesn't have them stored when it's merging in the new ones it doesn't include
all the keys like 'label', 'description', etc. If using the built-in endpoints/serializers or relying on these directly 
it can cause crashes.

#### 0.3.35 (2020-09-02)

Fixes

- Resolves issue introduced in 0.3.34 where unread count data only push would be sent but message isn't yet visible on
the API endpoints.

#### 0.3.34 (2020-09-02)

Fixes

- Inbox message endpoint for retrieving list of messages should only show them once they've been logged, otherwise the
callback hooks don't have a way to hide a message before it possibly shows depending on the latency between 
message processing time and the send_at time... it's possible a message could show up in the inbox briefly before it's
hidden because it wasn't supposed to be shown.

#### 0.3.33 (2020-08-07)

Fixes

- Path ids for preference id and medium id should always be underscores (eg app_push), not hyphens too, only needed
to change message_preferences to support both, not the ids.

#### 0.3.32 (2020-08-07)

Fixes

- When a Message was created, if send_at == now exactly then comms would be sent out but an unread count would not.

#### 0.3.31 (2020-08-05)

Fixes

- Strip leading and trailing whitespace on subject and body before saving to Message record

#### 0.3.30 (2020-08-05)

Improvement

- Allow hyphen or underscore URL paths on the pre-built endpoints, updated README to reflect preferred
usage of hyphens. In the future, will probably make it a configuration that defaults to hyphens.

#### 0.3.29 (2020-06-06)

Features

- Ability to create inbox only groups where all medium preferences are set to None so that it only ever shows up
within the inbox messages API.
- inbox_status command takes this into account and only requires there being a subject.txt and body.txt template.

Improvement

- Reduce number of times that the unread count silent push is sent when a Message is created,
processed for logs, etc.

#### 0.3.28 (2020-05-28)

Features

- Add `key` to Message objects returned in built-in endpoints

#### 0.3.27 (2020-05-27)

Fixes

- Broke Firebase backend by sending message instead of user, corrected

#### 0.3.26 (2020-05-27)

Fixes

- Send data-only (silent) app push with unread count when using the mark all read endpoint, wasn't working.

#### 0.3.25 (2020-05-27)

Features

- Add endpoint to fetch the current unread count for a `User`.

#### 0.3.16 (2020-05-20)

Fixes

- Fix Firebase backend
- Don't try to initial the Firebase Admin more than once or it'll crash, so try to get it first, then init.
- Switches EmailMessage send to use HTML instead of text content type.
- Handle error cases thrown by FCM
- Schema check on Message.data field so that it's a dictionary with key-value only and strings for values only

#### 0.3.5 (2020-05-18)

Features

- Will no longer send the email or SMS if they have not been verified. This behavior is on by default and looks for
the property `is_email_verified` and `is_sms_verified` when determining whether it `can_send` a `MessageLog`. Each of
these mediums verification check before sending can be disabled by setting `CHECK_IS_EMAIL_VERIFIED` or 
`CHECK_IS_SMS_VERIFIED` to `False` in the INBOX_CONFIG, they both default to `True`.

#### 0.3.4 (2020-05-12)

Fixes

- If all mediums for a message group are set to skip for a message key then `Message` was set to hide in Inbox, it 
will now show by default. If you have all mediums to always skip for a message key and still need custom logic to
hide the `Message` from the Inbox, then just define a `post_message_to_logs` hook for that message key.

#### 0.3.3 (2020-05-12)

Features

- Add ability to skip any medium for a message key. Since the mediums sent to is determined at the message group level,
we needed a mechanism to handle edge cases where a specific message key may want to skip over a medium.

#### 0.3.2 (2020-05-12)

Features

- Add utility method for saving messages, wraps up core of what the /users/{userId}/message_preferences endpoint
does when saving and offers it as a utility method. `utils.save_message_preferences`

#### 0.3.1 (2020-05-07)

Fixes

- Fix issue with `inbox_status` management command where it was using the group id instead of the message keys to find
templates.

#### 0.3.0 (2020-05-06)

Features

- Now you can add a `data` object onto each `message_group` on INBOX_CONFIG, this data will be available in templates
as `data_group` and returned on each message.group object on the Messages API endpoints.

Fixes

- If a `Message` never generates a `MessageLog` because they are cancelled, etc then the `Message` should not show up 
in the Inbox.

#### 0.2.6 (2020-05-06)

Features

- By default, `Message.create` will no longer throw Exceptions, it's handled by a setting in `INBOX_CONFIG`, and can
be overridden per call if needed.
- Define hooks that are called when a message is being transitioned to message logs. `Message`s are no longer
immediately put in `MessageLog`s, only when they are ready to be sent. When this happens, three lifecycle hooks are
fired that can be hooked into to perform additional tasks, prevent sending, etc.

Fixes

- Text templates are no longer autoescaped so that characters don't end up as HTML entities when not being used in an
HTML context.
- Collapsing new-lines on subject happens for all mediums now.

---

#### 0.2.5 (2020-05-05)

Features

- “Silent” data-only push is now sent when inbox message unread count has changed. This is only sent if at least one 
`Group` is configured with `app_push: true/false`.