import django.dispatch

# Arguments: user, count
unread_count = django.dispatch.Signal()

# Arguments: user, delta
message_preferences_changed = django.dispatch.Signal()
