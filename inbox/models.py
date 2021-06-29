import inspect
import json
import logging
import os
import uuid
from enum import Enum
from functools import lru_cache
from typing import List, Union, Tuple, Set

from annoying.fields import AutoOneToOneField
from django.contrib.auth import get_user_model
from django.core import exceptions
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import models
from django.db.models import UniqueConstraint, Q
from django.db.models.manager import BaseManager
from django.template import loader, TemplateDoesNotExist
from django.utils import timezone
from django.utils.module_loading import import_string
from django_enumfield import enum
from jsonschema import validate, exceptions as jsonschema_exceptions
from toolz import merge
import django

if django.VERSION >= (3, 1):
    from django.db.models import JSONField
else:
    from django.contrib.postgres.fields import JSONField

from inbox import settings as inbox_settings
from inbox.constants import MessageMedium, MessageLogStatus, MessageLogFailureReason
from inbox.core.app_push.message import AppPushMessage
from inbox.signals import unread_count, message_preferences_changed

User = get_user_model()
logger = logging.getLogger(__name__)

MEDIUMS = ('app_push', 'email', 'sms', 'web_push',)  # TODO Consolidate by using the enum below
hooks_module = inbox_settings.get_config()['HOOKS_MODULE']


class MessageQuerySet(models.QuerySet):

    def live(self):
        now = timezone.now()
        return self.filter(send_at__lte=now, is_hidden=False, deleted_at__isnull=True, is_logged=True)


class MessageManager(BaseManager.from_queryset(MessageQuerySet)):

    def create(self, *args, fail_silently=None, **kwargs):

        if fail_silently is None:
            fail_silently = inbox_settings.get_config()['MESSAGE_CREATE_FAIL_SILENTLY']

        if 'send_at' in kwargs and kwargs['send_at'] is None:
            kwargs['send_at'] = Message().send_at

        res = None
        try:
            res = super().create(*args, **kwargs)
        except Exception as e:
            if not fail_silently:
                raise e

        return res

    def exists(self, message_ids: Union[Set[str], List[str], str]) -> Tuple[Set[str], Set[str]]:
        """
        Pass it a list or set of message_ids and it will return the ones that have been sent to
        and the ones who haven't as sets in a tuple. Message Id order is not guaranteed, duplicates are removed.
        """
        if not isinstance(message_ids, list):
            message_ids = [message_ids]

        message_ids = set(message_ids)

        existing_message_ids = set(self.values_list('message_id', flat=True).filter(message_id__in=message_ids))
        missing_message_ids = message_ids - existing_message_ids

        return existing_message_ids, missing_message_ids

    def mark_all_read(self, user_id: int):
        now = timezone.now()
        updated_count = self.filter(user_id=user_id, read_at__isnull=True, deleted_at__isnull=True,
                                    is_hidden=False).update(read_at=now)

        if updated_count:
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return
            else:
                Message.send_unread_count_app_push(user, 0)
                unread_count.send(sender=Message, count=0)

    def unread_count(self, user_id: int):
        return self.filter(user_id=user_id, send_at__lte=timezone.now(), read_at__isnull=True, deleted_at__isnull=True,
                           is_hidden=False).count()


@lru_cache()
def get_message_groups():
    return inbox_settings.get_config()['MESSAGE_GROUPS']


@lru_cache()
def get_message_group(id_: str):
    message_groups = get_message_groups()

    for message_group in message_groups:
        if message_group['id'] == id_:
            return message_group

    return None


@lru_cache()
def is_app_push_enabled():
    """
    If any of the preferences are set to true/false for app_push then it's enabled.
    :return: boolean
    """

    message_groups = get_message_groups()

    for message_group in message_groups:
        if message_group['preference_defaults']['app_push'] is not None:
            return True

    return False


def get_message_group_default():
    return get_message_groups()[0]['id']


def validate_group(value):
    return value in [message_group['id'] for message_group in get_message_groups()]


def default_message_id():
    return str(uuid.uuid4())


def perform_user_maintenance(user: User):
    """
    Supports:
    * max_age
    * max_age + min_count
    * max_age + min_count + max_count
    * max_age + min_count + max_count + min_age
    * max_age + max_count
    * max_age + max_count + min_age
    * max_count
    * max_count + min_age

    Ignores max_age if min_count is not defined.
    Ignores max_count if min_age is not defined.

    :param user:
    :return: None
    """

    max_age = inbox_settings.get_config()['PER_USER_MESSAGES_MAX_AGE']
    min_count = inbox_settings.get_config()['PER_USER_MESSAGES_MIN_COUNT']
    max_count = inbox_settings.get_config()['PER_USER_MESSAGES_MAX_COUNT']
    min_age = inbox_settings.get_config()['PER_USER_MESSAGES_MIN_AGE']

    if not any((max_age, min_count, max_count, min_age)):
        return

    now = timezone.now()

    messages = Message.objects.filter(user=user).live()

    max_age_at = now - max_age if max_age else None
    min_age_at = now - min_age if min_age else None

    for k, message in enumerate(messages):
        if min_count and k < min_count:
            continue

        if max_age_at and message.send_at < max_age_at:
            message.delete(reason=MessageDeleteReason.MAINTENANCE)
            continue

        if min_age_at and message.send_at >= min_age_at:
            continue

        if max_count and k >= max_count:
            message.delete(reason=MessageDeleteReason.MAINTENANCE)
            continue


class MessageDeleteReason(Enum):
    SOFT = 1
    FORCE = 2
    MAINTENANCE = 3


class Message(models.Model):

    class Meta:
        constraints = [
            UniqueConstraint(fields=['user', 'message_id'], name='unique_user_message_id')
        ]
        indexes = [
            models.Index(fields=['-send_at', 'read_at', 'deleted_at', 'is_hidden']),
        ]
        ordering = ('-send_at',)

    objects = MessageManager()

    base_subject_template = None
    base_body_template = None

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    key = models.CharField(max_length=255, db_index=True)
    subject = models.TextField(blank=True, db_index=True, null=True)
    body = models.TextField(blank=True, db_index=False, null=True)
    data = JSONField(blank=True, db_index=True, null=True,
                     help_text='Arbitrary data that can be used by consuming '
                               ' clients/signal listeners as needed (eg needing'
                               ' extra data to pass with Gmail emails for actions,'
                               ' extra data for push notifications for interactive'
                               ' notifications.')
    data_email = JSONField(blank=True, db_index=True, null=True,
                           help_text='Arbitrary data that is included with data when creating email templates.')
    message_id = models.CharField(db_index=True, max_length=255, null=True, blank=True,
                                  help_text='Explicitly specifying a message id enables message de-duplication '
                                            'per user.')
    group_id = models.CharField(db_index=True, default=get_message_group_default(), max_length=255,
                                validators=(validate_group,))
    is_hidden = models.BooleanField(default=False, help_text="There may be cases you want to generate a message so "
                                                             "that it can trigger communication in other channels but "
                                                             "you don't want it to show up in the user's inbox, set "
                                                             "this flag to true.")
    send_at = models.DateTimeField(default=timezone.now)
    is_logged = models.BooleanField(default=False)
    is_forced = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='Marked Read At')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Created')
    updated_at = models.DateTimeField(auto_now=True, db_index=True, verbose_name='Updated')
    deleted_at = models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='Deleted')

    @property
    def is_read(self):
        return bool(self.read_at)

    @property
    def group(self):
        group = get_message_group(self.group_id)

        return {
            'id': group['id'],
            'label': group['label'],
            'data': group['data']
        }

    @property
    def body_full(self):
        return self._build_body()

    @is_read.setter
    def is_read(self, value: bool):
        if not value:
            self.read_at = None
        elif not self.read_at:
            self.read_at = timezone.now()

    def clean(self):
        group = self._get_group_from_key()
        if not group:
            raise ValidationError({'key': [f'"{self.key}" does not exist in any group.']})
        else:
            self.group_id = group['id']

        subject_template, body_template = self._get_base_templates()

        if self.key and not subject_template:
            raise ValidationError({'key': [f'Subject template for "{self.key}" does not exist.',]})

        if self.key and not body_template:
            raise ValidationError({'key': [f'Body template for "{self.key}" does not exist.',]})

    def save(self, *args, **kwargs):
        is_new = not self.id
        self.full_clean()

        now = timezone.now()
        send_unread_count = False
        perform_maintenance = False
        if is_new:
            if self.is_forced:
                self.send_at = now
                self.message_id = None

            self.subject = self._build_subject()
            self.body = self._build_body_excerpt()
        else:
            if self.is_logged and now >= self.send_at:
                send_unread_count = True
                perform_maintenance = True

        super().save(*args, **kwargs)

        # If the message is in the future we don't need to send the unread count
        if send_unread_count:
            self._send_unread_count()

        if perform_maintenance:
            perform_user_maintenance(self.user)

    def delete(self, using=None, keep_parents=False, reason=MessageDeleteReason.SOFT):
        if reason == MessageDeleteReason.FORCE or (reason == MessageDeleteReason.MAINTENANCE and not self.message_id):
            super().delete(using=using, keep_parents=keep_parents)
        else:
            self.deleted_at = timezone.now()
            self.save(using=using)

        self._send_unread_count()

        return 1

    def _get_base_templates(self):
        """
        We have to have at least the base subject and body templates to build the inbox content, if we don't have either
        then it's an invalid message key.
        :return:
        """
        template_name = f'inbox/{self.key}/subject.txt'
        try:
            self.base_subject_template = loader.get_template(template_name)
        except TemplateDoesNotExist:
            pass

        template_name = f'inbox/{self.key}/body.html'
        try:
            self.base_body_template = loader.get_template(template_name)
        except TemplateDoesNotExist:
            pass

        if not self.base_body_template:
            template_name = f'inbox/{self.key}/body.txt'
            try:
                self.base_body_template = loader.get_template(template_name)
            except TemplateDoesNotExist:
                pass

        return self.base_subject_template, self.base_body_template

    def _render_from_templates(self, templates):
        template = None
        autoescape = True
        for template_name, autoescape in templates:
            try:
                template = loader.get_template(template_name)
            except TemplateDoesNotExist:
                continue
            else:
                break

        template.backend.engine.autoescape = autoescape
        context = self._get_context_for_template()
        return template.render(context).strip()

    def _build_subject(self):
        templates = (
            (f'inbox/{self.key}/subject.txt', False),
        )

        res = self._render_from_templates(templates)

        return ''.join(res.splitlines()).strip()

    def _build_body_excerpt(self):
        templates = (
            (f'inbox/{self.key}/body_excerpt.html', True),
            (f'inbox/{self.key}/body_excerpt.txt', False),
            (f'inbox/{self.key}/body.html', True),
            (f'inbox/{self.key}/body.txt', False),
        )

        return self._render_from_templates(templates)

    def _build_body(self):
        templates = (
            (f'inbox/{self.key}/body.html', True),
            (f'inbox/{self.key}/body.txt', False),
        )

        return self._render_from_templates(templates)

    def _get_context_for_template(self):
        return {
            'user': self.user,
            'data': self.data,
            'data_email': self.data_email,
            'data_group': self.group
        }

    @staticmethod
    def send_unread_count_app_push(user, count):
        if not inbox_settings.get_config()['DISABLE_NEW_DATA_SILENT_APP_PUSH'] and is_app_push_enabled():
            AppPushMessage(user, None, None, data={'inbox_message_unread_count': str(count)}).send()

    def _send_unread_count(self):
        # Send out new unread count
        count = Message.objects.unread_count(user_id=self.user.pk)

        self.send_unread_count_app_push(self.user, count)

        unread_count.send(sender=self.__class__, count=count)

    def _get_group_from_key(self):
        for message_group in get_message_groups():
            if self.key in message_group['message_keys']:
                return message_group

        return None

    def should_skip_medium(self, medium):
        if medium not in MEDIUMS:
            raise ValueError('Invalid medium')

        message_group = self._get_group_from_key()

        if self.key in message_group[f'skip_{medium}']:
            return True

        return False


class MessageLog(models.Model):
    """
    MessageLog are used to queue up messages to be sent, usually by some sort of cron or before a request finishes
    (although not recommended). It's not a background job system in itself, if you want true background capability
    you need to setup a separate process like a cron job that can process objects here and send then to a background
    job or queue system that handles the jobs in the background outside of this context.
    """
    class Meta:
        indexes = [
            models.Index(fields=['-send_at', 'status']),
        ]

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='logs')
    medium = enum.EnumField(MessageMedium)
    send_at = models.DateTimeField(db_index=True)  # This is from the parent Message
    status = enum.EnumField(MessageLogStatus, default=MessageLogStatus.NEW)
    failure_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Created')

    @property
    def can_send(self):
        user = self.message.user
        message_group = self.message.group

        try:
            can_send_hook = import_string(f'{hooks_module}.{self.message.key}.can_send')

            return bool(can_send_hook(self))
        except (ImportError, ModuleNotFoundError) as e:
            pass

        if self.medium == MessageMedium.APP_PUSH:
            can_send_hook = None
            try:
                can_send_hook = import_string(f'{hooks_module}.{self.message.key}.can_send_app_push')
            except (ImportError, ModuleNotFoundError) as e:
                pass

            if can_send_hook:
                return bool(can_send_hook(self))

            if not user.notification_key:
                self.status = MessageLogStatus.FAILED
                self.failure_reason = MessageLogFailureReason.MISSING_APP_PUSH_KEY
                return False

        if self.medium == MessageMedium.EMAIL:
            can_send_hook = None
            try:
                can_send_hook = import_string(f'{hooks_module}.{self.message.key}.can_send_email')
            except (ImportError, ModuleNotFoundError) as e:
                pass

            if can_send_hook:
                return bool(can_send_hook(self))

            if inbox_settings.get_config()['CHECK_IS_EMAIL_VERIFIED'] and not user.is_email_verified:
                self.status = MessageLogStatus.FAILED
                self.failure_reason = MessageLogFailureReason.EMAIL_NOT_VERIFIED
                return False

        if self.medium == MessageMedium.SMS:
            can_send_hook = None
            try:
                can_send_hook = import_string(f'{hooks_module}.{self.message.key}.can_send_sms')
            except (ImportError, ModuleNotFoundError) as e:
                pass

            if can_send_hook:
                return bool(can_send_hook(self))

            if inbox_settings.get_config()['CHECK_IS_SMS_VERIFIED'] and not user.is_sms_verified:
                self.status = MessageLogStatus.FAILED
                self.failure_reason = MessageLogFailureReason.SMS_NOT_VERIFIED
                return False

        preference = next((g for g in user.message_preferences.groups if g['id'] == message_group['id']))

        if preference.get(self.medium.name.lower()):
            return True
        else:
            self.status = MessageLogStatus.SKIPPED_FOR_PREF

        return False

    def send(self):
        if self.medium == MessageMedium.APP_PUSH:
            self.send_push_notification()
        if self.medium == MessageMedium.EMAIL:
            self.send_email()

    def send_push_notification(self):
        subject = self._build_subject()
        body = self._build_body()

        AppPushMessage(self.message.user, subject, body, data=self.message.data, message_log=self).send()

    def send_email(self):
        subject = self._build_subject()
        body = self._build_body()

        msg = EmailMessage(subject, body, to=[self.message.user.email])
        msg.content_subtype = "html"
        try:
            msg.send()
        except Exception as e:
            msg = str(e)
            self.status = MessageLogStatus.FAILED
            self.failure_reason = msg
            logger.error(msg)

    def _get_context_for_template(self):
        return {
            'user': self.message.user,
            'data': self.message.data,
            'data_email': self.message.data_email,
            'data_group': self.message.group
        }

    @staticmethod
    def _get_subject_template_names(key: str, medium: MessageMedium = None, debug=False):
        template_names = []

        if medium:
            template_names = [
                (f'inbox/{key}/subject_{medium.name.lower()}.txt', False)
            ]

        template_names.append(
            (f'inbox/{key}/subject.txt', True)
        )

        if not debug:
            template_names = [tn[0] for tn in template_names]

        return template_names

    def _build_subject(self):
        try:
            template = loader.select_template(self._get_subject_template_names(self.message.key, self.medium))
        except TemplateDoesNotExist:
            raise ValidationError({'key': [f'Subject template for "{self.message.key}/{self.medium.name.lower()}" '
                                           f'does not exist.']})

        context = self._get_context_for_template()

        autoescape = True
        if template.origin.template_name.endswith('txt'):
            autoescape = False

        template.backend.engine.autoescape = autoescape
        subject = template.render(context)

        if inbox_settings.get_config()['TESTING_MEDIUM_OUTPUT_PATH']:
            from inbox.test.utils import dump_template
            dump_template(template.template.name, subject)

        return ''.join(subject.splitlines())

    @staticmethod
    def _get_body_template_names(key: str, medium: MessageMedium = None, debug=False):
        template_names = []

        # Ordering is important here as the loader will use the first one it finds
        if medium and medium != MessageMedium.EMAIL:
            template_names.extend([
                (f'inbox/{key}/body_{medium.name.lower()}.txt', False),
                (f'inbox/{key}/body.txt', True)
            ])
        elif medium == MessageMedium.EMAIL:
            template_names.append(
                (f'inbox/{key}/body_{medium.name.lower()}.html', True)
            )
        else:
            # Fallback to generate the body for the Inbox object's body
            template_names.extend([
                (f'inbox/{key}/body.html', False),
                (f'inbox/{key}/body.txt', True),
                (f'inbox/{key}/body_excerpt.html', False),
                (f'inbox/{key}/body_excerpt.txt', False),
            ])

        if not debug:
            template_names = [tn[0] for tn in template_names]

        return template_names

    def _build_body(self):
        try:
            template = loader.select_template(self._get_body_template_names(self.message.key, self.medium))
        except TemplateDoesNotExist:
            raise ValidationError({'key': [f'Body template for "{self.message.key}/{self.medium.name.lower()}" does not exist.']})

        autoescape = True
        if template.origin.template_name.endswith('txt'):
            autoescape = False

        context = self._get_context_for_template()
        template.backend.engine.autoescape = autoescape
        body = template.render(context)

        if inbox_settings.get_config()['TESTING_MEDIUM_OUTPUT_PATH']:
            from inbox.test.utils import dump_template
            dump_template(template.template.name, body)

        return body


# TODO Move to own django lib
class JSONSchemaField(JSONField):

    def __init__(self, *args, **kwargs):
        self.schema = kwargs.pop('schema', None)
        super().__init__(*args, **kwargs)

    @property
    def _schema_data(self):
        model_file = inspect.getfile(self.model)
        dirname = os.path.dirname(model_file)
        # schema file related to model.py path
        p = os.path.join(dirname, self.schema)
        with open(p, 'r') as file:
            return json.loads(file.read())

    def _validate_schema(self, value):

        # Disable validation when migrations are faked
        if self.model.__module__ == '__fake__':
            return True
        try:
            status = validate(value, self._schema_data)
        except jsonschema_exceptions.ValidationError as e:
            raise exceptions.ValidationError(e.message, code='invalid')
        return status

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        self._validate_schema(value)

    def pre_save(self, model_instance, add):
        value = super().pre_save(model_instance, add)
        if value or not self.null:
            self._validate_schema(value)
        return value


def get_default_preference_ids():
    return [dp['id'] for dp in get_default_preferences()]


def _get_props(message_group, include_all_keys):

    d = {'id': message_group['id']}
    if include_all_keys:
        d.update({
            'label': message_group['label'],
            'description': message_group['description'],
            'data': message_group['data']
        })

    return d


def get_default_preferences(include_all_keys=False):
    message_groups_with_preference = filter(lambda message_group: message_group['is_preference'], get_message_groups())

    default_preferences = [{**_get_props(mg, include_all_keys),
                            **mg['preference_defaults']} for mg in message_groups_with_preference]

    # Remove any null mediums, they are disabled
    for k, default_preference in enumerate(default_preferences):
        default_preferences[k] = {k: v for k, v in default_preference.items() if k in ('id',
                                                                                       'label',
                                                                                       'description',
                                                                                       'data') or v is not None}

    return default_preferences


def reconcile_default_preferences(preferences):
    """
    This method shouldn't be used to clean before storing but just to clean before presenting in API

    - Removes preferences that are no longer in defaults
    - Merge default for each group so that if a group medium is missing, it will exist now
    - Remove preference mediums that are set to None in defaults
    - Add in groups (eg new groups added)
    :param preferences:
    :return: preferences
    """

    mediums = ('app_push', 'email', 'sms', 'web_push')
    default_preference_ids = get_default_preference_ids()
    # Removes preferences that are no longer in defaults
    preferences = [p for p in preferences if p['id'] in default_preference_ids]

    # Merge default for each group so that if a group medium is missing, it will exist now
    for k, preference in enumerate(preferences):
        # Find default preference for this id
        default_preference = next((dp for dp in get_default_preferences(include_all_keys=True) if dp['id'] == preference['id']))
        preferences[k] = merge(default_preference, preference)

    # Remove preference mediums that are set to None in defaults
    for k, preference in enumerate(preferences):
        # Find default preference for this id
        default_preference = next((dp for dp in get_default_preferences() if dp['id'] == preference['id']))

        for medium in mediums:
            if medium not in default_preference and medium in preferences[k]:
                del preferences[k][medium]

    for k, default_preference in enumerate(get_default_preferences(include_all_keys=True)):
        try:
            next((p for p in preferences if p['id'] == default_preference['id']))
        except StopIteration:
            preferences.append(default_preference)

    # Fix any sorting issues
    preferences_sorted = []
    for k, pref in enumerate(get_default_preferences()):
        preferences_sorted.append(next((p for p in preferences if p['id'] == pref['id'])))

    preferences = preferences_sorted

    return preferences


def reconcile_preferences(stored_preferences, new_preferences):
    """
    This is the method you'll want to use to pass in what's already stored for the user, and the new updates from the
    user, reconcile them together so that it can be stored back if desired. We don't clear out any existing that may
    no longer be present in defaults in case you want to keep storing them, bring them back, etc. Suggestion is to
    filter those out before returning them to any client.

    :param stored_preferences:
    :param new_preferences:
    :return: preferences
    """

    preferences = []
    preference_ids = []
    # First collapse the new list so that any preferences with same id prefer the later in the list and filter out
    #  anything that's not already stored or in defaults (eg invalid or legacy prefs)
    default_preference_ids = get_default_preference_ids()
    stored_preference_ids = [dp['id'] for dp in stored_preferences]
    new_preferences.reverse()
    for p in new_preferences:
        if (p['id'] in default_preference_ids or p['id'] in stored_preference_ids) and p['id'] not in preference_ids:
            preference_ids.append(p['id'])
            preferences.append(p)

    preferences.reverse()

    # Merge in missing stored preferences
    for spk, stored_pref in enumerate(stored_preferences):
        pref = next(((pk, p) for pk, p in enumerate(preferences) if p['id'] == stored_pref['id']), None)
        if not pref:
            preferences.append(stored_pref)

    # Merge in missing default preferences, usually most beneficial when new preferences are added
    for dpk, default_pref in enumerate(get_default_preferences()):
        pref = next(((pk, p) for pk, p in enumerate(preferences) if p['id'] == default_pref['id']), None)
        if not pref:
            preferences.append(default_pref)

    # Fix any sorting issues
    preferences_sorted = []
    for k, pref in enumerate(get_default_preferences()):
        sorted_pref = next((p for p in preferences if p['id'] == pref['id']))
        if sorted_pref:
            preferences_sorted.append(sorted_pref)

    # Loop over preferences, if not in pref sorted, append to bottom so they are still stored
    for k, pref in enumerate(preferences):
        try:
            next((p for p in preferences_sorted if p['id'] == pref['id']))
        except StopIteration:
            preferences_sorted.append(pref)

    preferences = preferences_sorted

    # Finally, go back over each preference and remove any invalid mediums
    for k, pref in enumerate(preferences):
        preferences[k] = {k: v for k, v in pref.items() if k == 'id' or k in MEDIUMS}

    return preferences


class MessagePreferences(models.Model):
    user = AutoOneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='message_preferences')

    _groups = JSONSchemaField(blank=True, db_index=True, null=True, default=get_default_preferences,
                              db_column='groups', schema='message_preference_groups.schema.json')

    @property
    def groups(self):
        return reconcile_default_preferences(self._groups)

    @groups.setter
    def groups(self, value):
        self._groups = reconcile_preferences(self._groups, value)

    def save(self, **kwargs):

        original_message_preferences = MessagePreferences.objects.filter(pk=self.pk).first()

        if original_message_preferences:
            pass
            # TODO Loop over every key in the current preferences, look it up in the original
            #  if it doesn't exist in the original, then it's changed
            #  if you find it, loop over the medium values, if any changed, then it's changed
            #  if changed, add group key to groups_changed list so that we can notify signal
            #  Keep track of each medium state change True -> False, False -> True, None -> True, None -> False,
            #  True -> None, False -> None, return list of groups an within that list of changes, with each change
            #  containing the medium, prev state, next state

        super().save(**kwargs)

        changed_message_preferences = self.delta(original_message_preferences) if original_message_preferences else []
        if changed_message_preferences:
            message_preferences_changed.send(sender=self.__class__, delta=changed_message_preferences)

    def delta(self, message_preferences):
        """
        Return the preferences from self that have different medium values from the `message_preferences`

        :param message_preferences:
        :return: message_preferences: MessagePreferences
        """
        changed_message_preferences = []

        for group in self.groups:
            original_group = next((g for g in message_preferences.groups if g['id'] == group['id']))

            if not original_group:
                continue

            new_group = group.copy()
            mediums = {}
            for medium in MessageMedium.keys():
                current = group.get(medium)
                if current != original_group.get(medium):
                    mediums.update(**{medium: current})
                else:
                    new_group.pop(medium, None)

            if mediums:
                new_group.update(**mediums)
                changed_message_preferences.append(new_group)

        return changed_message_preferences
