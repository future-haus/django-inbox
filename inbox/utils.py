from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from inbox import settings as inbox_settings
from inbox.constants import MessageLogStatus, MessageMedium
from inbox.models import MessageLog, Message, get_default_preference_ids, MessagePreferences

hooks_module = inbox_settings.get_config()['HOOKS_MODULE']


def process_new_messages():
    messages = Message.objects \
                   .select_related('user') \
                   .select_for_update(skip_locked=True).filter(send_at__lte=timezone.now(),
                                                               is_logged=False)[:25]

    with transaction.atomic():
        for message in messages:

            # Determine what mediums, based on the config, that it can be sent to. We'll filter out by user's
            # preferences when processing the logs to actually send
            mediums = [k for k, v in message._get_group_from_key()['preference_defaults'].items() if v is not None]

            for medium in mediums:
                medium_enum = MessageMedium.get(medium.upper())
                message_log = MessageLog(message=message, medium=medium_enum, send_at=message.send_at)

                pre_message_log_save = None
                if hooks_module:
                    try:
                        pre_message_log_save = import_string(f'{hooks_module}.{message.key}.pre_message_log_save')
                    except (ImportError, ModuleNotFoundError) as e:
                        pass

                if pre_message_log_save:
                    message_log = pre_message_log_save(message, medium_enum, message_log)

                if message_log:
                    message_log.save()

                post_message_log_save = None
                if hooks_module:
                    try:
                        post_message_log_save = import_string(f'{hooks_module}.{message.key}.post_message_log_save')
                    except (ImportError, ModuleNotFoundError):
                        pass

                # Even if message_log is None we call the post_message_log_save for maximum flexibility
                if post_message_log_save:
                    post_message_log_save(message, medium_enum, message_log)

            post_message_to_logs = None
            if hooks_module:
                try:
                    post_message_to_logs = import_string(f'{hooks_module}.{message.key}.post_message_to_logs')
                except (ImportError, ModuleNotFoundError) as e:
                    pass

            if post_message_to_logs:
                message = post_message_to_logs(message)

            if message.logs.count() == 0:
                message.is_hidden = True

            message.is_logged = True
            message.save()


def process_new_message_logs():
    message_logs = MessageLog.objects \
                       .select_related('message', 'message__user') \
                       .select_for_update(skip_locked=True).filter(send_at__lte=timezone.now(),
                                                                   status=MessageLogStatus.NEW)[:25]

    with transaction.atomic():
        for message_log in message_logs:
            if message_log.can_send:
                message_log.status = MessageLogStatus.SENT
                message_log.send()
            else:
                message_log.status = MessageLogStatus.SKIPPED_FOR_PREF

            message_log.save()


def save_message_preferences(message_preferences: MessagePreferences, data, preference_id: int = None,
                             medium_id: int = None):
    """

    :param message_preferences: MessagePreferences
        existing message preferences
    :param data:
        either individual boolean if targeting a specific preference_id and medium_id
    :param preference_id: int, optional
    :param medium_id: int, optional

    :return: message_preferences: MessagePreferences
        saved message preferences
    """
    if preference_id and preference_id not in get_default_preference_ids():
        raise ValueError(
            {'preference_id': [f'The preference_id ({preference_id}) specified in the path is invalid.']}
        )
    if medium_id and MessageMedium.get(medium_id.upper()) is None:
        raise ValueError(
            {'medium_id': [f'The medium_id ({medium_id}) specified in the path is invalid.']}
        )
    if preference_id and medium_id:

        message_preferences = MessagePreferences.objects.select_for_update().get(pk=message_preferences.pk)
        for k, group in enumerate(message_preferences._groups):
            if group['id'] == preference_id:
                message_preferences._groups[k][medium_id] = data
                break
    elif data:
        message_preferences.groups = data

    message_preferences.save()

    return message_preferences
