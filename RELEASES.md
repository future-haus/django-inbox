# Releases

### 0.3.13 (2020-05-20)

Fixes

- Fix Firebase backend
- Don't try to initial the Firebase Admin more than once or it'll crash, so try to get it first, then init.
- Switches EmailMessage send to use HTML instead of text content type.

### 0.3.5 (2020-05-18)

Features

- Will no longer send the email or SMS if they have not been verified. This behavior is on by default and looks for
the property `is_email_verified` and `is_sms_verified` when determining whether it `can_send` a `MessageLog`. Each of
these mediums verification check before sending can be disabled by setting `CHECK_IS_EMAIL_VERIFIED` or 
`CHECK_IS_SMS_VERIFIED` to `False` in the INBOX_CONFIG, they both default to `True`.

### 0.3.4 (2020-05-12)

Fixes

- If all mediums for a message group are set to skip for a message key then `Message` was set to hide in Inbox, it 
will now show by default. If you have all mediums to always skip for a message key and still need custom logic to
hide the `Message` from the Inbox, then just define a `post_message_to_logs` hook for that message key.

### 0.3.3 (2020-05-12)

Features

- Add ability to skip any medium for a message key. Since the mediums sent to is determined at the message group level,
we needed a mechanism to handle edge cases where a specific message key may want to skip over a medium.

### 0.3.2 (2020-05-12)

Features

- Add utility method for saving messages, wraps up core of what the /users/{userId}/message_preferences endpoint
does when saving and offers it as a utility method. `utils.save_message_preferences`

### 0.3.1 (2020-05-07)

Fixes

- Fix issue with `inbox_status` management command where it was using the group id instead of the message keys to find
templates.

### 0.3.0 (2020-05-06)

Features

- Now you can add a `data` object onto each `message_group` on INBOX_CONFIG, this data will be available in templates
as `data_group` and returned on each message.group object on the Messages API endpoints.

Fixes

- If a `Message` never generates a `MessageLog` because they are cancelled, etc then the `Message` should not show up 
in the Inbox.

### 0.2.6 (2020-05-06)

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

### 0.2.5 (2020-05-05)

Features

- “Silent” data-only push is now sent when inbox message unread count has changed. This is only sent if at least one 
`Group` is configured with `app_push: true/false`.