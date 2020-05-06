# Releases

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