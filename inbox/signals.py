import django.dispatch

unread_count = django.dispatch.Signal(providing_args=['count'])
message_preferences_changed = django.dispatch.Signal(providing_args=['changed_groups'])  # TODO This needs to be fired off still
