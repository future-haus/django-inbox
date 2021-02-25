import django.dispatch

# Arguments: "count"
unread_count = django.dispatch.Signal()

# Arguments: "delta"
message_preferences_changed = django.dispatch.Signal()
