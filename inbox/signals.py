import django.dispatch

unread_count = django.dispatch.Signal(providing_args=['count'])
message_preferences_changed = django.dispatch.Signal(providing_args=['delta'])
