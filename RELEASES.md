# Releases

### Next Release

Features

- By default, `Message.create` will no longer throw Exceptions, it's handled by a setting in `INBOX_CONFIG`, and can
be overridden per call if needed.

---

### 0.2.5 (2020-05-05)

Features

- “Silent” data-only push is now sent when inbox message unread count has changed. This is only sent if at least one 
`Group` is configured with `app_push: true/false`.