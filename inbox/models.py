import inspect
import json
import os
import uuid

from annoying.fields import AutoOneToOneField
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.core import exceptions
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import models, transaction
from django.db.models import UniqueConstraint
from django.db.models.manager import BaseManager
from django.template import loader, TemplateDoesNotExist
from django.utils import timezone
from django_enumfield import enum
from jsonschema import validate, exceptions as jsonschema_exceptions
from toolz import merge

from inbox import settings as inbox_settings
from inbox.constants import MessageMedium, MessageLogStatus, MessageLogFailureReason
from inbox.core.app_push.message import AppPushMessage
from inbox.signals import message_preferences_changed, unread_count
from inbox.test.utils import dump_template

User = get_user_model()

MEDIUMS = ('app_push', 'email', 'sms', 'web_push',)  # TODO Consolidate by using the enum below


class MessageQuerySet(models.QuerySet):

    def live(self):
        now = timezone.now()
        return self.filter(send_at__lte=now, is_hidden=False, deleted_at__isnull=True)


class MessageManager(BaseManager.from_queryset(MessageQuerySet)):

    def mark_all_read(self, user_id: int):
        now = timezone.now()
        updated_count = self.filter(user_id=user_id, read_at__isnull=True, deleted_at__isnull=True,
                                    is_hidden=False).update(read_at=now)

        if updated_count:
            unread_count.send(sender=Message, count=0)

    def unread_count(self, user_id: int):
        return self.filter(user_id=user_id, read_at__isnull=True, deleted_at__isnull=True,
                           is_hidden=False).count()


def get_message_groups():
    return inbox_settings.get_config()['MESSAGE_GROUPS']


def get_message_group_default():
    return get_message_groups()[0]['id']


def validate_group(value):
    return value in [message_group['id'] for message_group in get_message_groups()]


def default_message_id():
    return str(uuid.uuid4())


class Message(models.Model):

    class Meta:
        constraints = [
            UniqueConstraint(fields=['user', 'message_id'], name='unique_user_message_id')
        ]
        indexes = [
            models.Index(fields=['-send_at', 'is_hidden', 'deleted_at']),
        ]
        ordering = ('-send_at',)

    objects = MessageManager()

    base_subject_template = None
    base_body_template = None

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    key = models.CharField(max_length=255, db_index=True)
    subject = models.TextField(blank=True, db_index=True, null=True)
    body = models.TextField(blank=True, db_index=True, null=True)
    data = JSONField(blank=True, db_index=True, null=True,
                     help_text='Arbitrary data that can be used by consuming '
                               ' clients/signal listeners as needed (eg needing'
                               ' extra data to pass with Gmail emails for actions,'
                               ' extra data for push notifications for interactive'
                               ' notifications.')
    data_email = JSONField(blank=True, db_index=True, null=True,
                           help_text='Arbitrary data that is included with data when creating email templates.')
    message_id = models.CharField(db_index=True, max_length=255, default=default_message_id,
                                  help_text='Explicitly specifying a message id enables message de-duplication '
                                            'per user.')
    group = models.CharField(db_index=True, default=get_message_group_default(), max_length=255,
                             validators=(validate_group,))
    is_hidden = models.BooleanField(default=False, help_text="There may be cases you want to generate a message so "
                                                             "that it can trigger communication in other channels but "
                                                             "you don't want it to show up in the user's inbox, set "
                                                             "this flag to true.")
    send_at = models.DateTimeField(db_index=True, default=timezone.now)
    read_at = models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='Marked Read At')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Created')
    updated_at = models.DateTimeField(auto_now=True, db_index=True, verbose_name='Updated')
    deleted_at = models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='Deleted')

    @property
    def is_read(self):
        return bool(self.read_at)

    @is_read.setter
    def is_read(self, value: bool):
        if not value:
            self.read_at = None
        elif not self.read_at:
            self.read_at = timezone.now()

    def clean(self):
        # TODO Verify message key exists in a message group

        subject_template, body_template = self._get_base_templates()

        if self.key and not subject_template:
            raise ValidationError({'key': [f'Subject template for "{self.key}" does not exist.',]})

        if self.key and not body_template:
            raise ValidationError({'key': [f'Body template for "{self.key}" does not exist.',]})

        group = self._get_group_from_key()
        if not group:
            raise ValidationError({'key': [f'Message Group not found for "{self.key}".']})
        else:
            self.group = group['id']

    def save(self, *args, **kwargs):
        is_new = not self.id
        self.full_clean()

        if is_new:
            self.subject = self._build_subject()
            self.body = self._build_body()

        with transaction.atomic():
            super().save(*args, **kwargs)

            if is_new:
                self.log()

        self._send_unread_count()

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(using=using)

        self._send_unread_count()

        return 1

    def log(self):
        # Determine what mediums, based on the config, that it can be sent to.
        # We don't filter out based on the user's preferences yet incase it's for the future, we determine whether
        #   to send right before actually sending
        mediums = [k for k, v in self._get_group_from_key()['preference_defaults'].items() if v is not None]

        for medium in mediums:
            MessageLog.objects.create(message=self, medium=MessageMedium.get(medium.upper()), send_at=self.send_at)

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

    def _build_subject(self):
        template_name = f'inbox/{self.key}/subject.txt'
        template = loader.get_template(template_name)
        context = self._get_context_for_template()
        return template.render(context)

    def _build_body(self):
        try:
            template_name = f'inbox/{self.key}/body.html'
            template = loader.get_template(template_name)
        except TemplateDoesNotExist:
            template_name = f'inbox/{self.key}/body.txt'
            template = loader.get_template(template_name)

        context = self._get_context_for_template()
        return template.render(context)

    def _get_context_for_template(self):
        return {
            'user': self.user,
            'data': self.data,
            'data_email': self.data_email
        }

    def _send_unread_count(self):
        # Send out new unread count
        count = Message.objects.unread_count(user_id=self.user.pk)
        unread_count.send(sender=self.__class__, count=count)

    def _get_group_from_key(self):
        for message_group in get_message_groups():
            if self.key in message_group['message_keys']:
                return message_group

        return None


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
    failure_reason = enum.EnumField(MessageLogFailureReason, default=None, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Created')

    @property
    def can_send(self):
        user = self.message.user
        message_group = self.message.group

        preference = next((g for g in user.message_preferences.groups if g['id'] == message_group))

        if preference.get(self.medium.name.lower()):
            return True

        return False

    def send(self):
        if self.medium == MessageMedium.APP_PUSH:
            self.send_push_notification()
        if self.medium == MessageMedium.EMAIL:
            self.send_email()

    def send_push_notification(self):
        subject = self._build_subject()
        body = self._build_body()

        AppPushMessage(self.message.user, subject, body, data=self.message.data).send()

    def send_email(self):
        subject = self._build_subject()
        body = self._build_body()

        EmailMessage(''.join(subject.splitlines()), body, to=[self.message.user.email]).send()

    def _get_context_for_template(self):
        return {
            'user': self.message.user,
            'data': self.message.data,
            'data_email': self.message.data_email
        }

    def _build_subject(self):
        template = None

        try:
            template_name = f'inbox/{self.message.key}/subject_{self.medium.name.lower()}.txt'
            template = loader.get_template(template_name)
        except TemplateDoesNotExist:
            pass

        if not template and self.medium == MessageMedium.APP_PUSH:
            template_name = f'inbox/{self.message.key}/subject.txt'
            template = loader.get_template(template_name)

        context = self._get_context_for_template()
        subject = template.render(context)

        if settings.INBOX_CONFIG['TESTING_MEDIUM_OUTPUT_PATH']:
            dump_template(template_name, subject)

        return subject

    def _build_body(self):
        template = None
        body_file_exts = {
            MessageMedium.APP_PUSH: 'txt',
            MessageMedium.EMAIL: 'html'
        }

        try:
            template_name = f'inbox/{self.message.key}/body_{self.medium.name.lower()}.{body_file_exts.get(self.medium)}'
            template = loader.get_template(template_name)
        except TemplateDoesNotExist:
            pass

        if not template and self.medium == MessageMedium.APP_PUSH:
            template_name = f'inbox/{self.message.key}/body.txt'
            template = loader.get_template(template_name)

        context = self._get_context_for_template()
        body = template.render(context)

        if settings.INBOX_CONFIG['TESTING_MEDIUM_OUTPUT_PATH']:
            dump_template(template_name, body)

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
            'description': message_group['description']
        })

    return d


def get_default_preferences(include_all_keys=False):
    message_groups_with_preference = filter(lambda message_group: message_group['is_preference'], get_message_groups())

    default_preferences = [{**_get_props(mg, include_all_keys),
                            **mg['preference_defaults']} for mg in message_groups_with_preference]

    # Remove any null mediums, they are disabled
    for k, default_preference in enumerate(default_preferences):
        default_preferences[k] = {k: v for k, v in default_preference.items() if k in ('id', 'label', 'description') or v is not None}

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

    for k, default_preference in enumerate(get_default_preferences()):
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

        # Get original and compare to know whether we need to sync with Sendgrid
        changed_message_preference = False
        groups_changed = []
        original_message_preference = MessagePreferences.objects.filter(pk=self.pk).first()

        if original_message_preference:
            pass
            # TODO Loop over every key in the current preferences, look it up in the original
            #  if it doesn't exist in the original, then it's changed
            #  if you find it, loop over the medium values, if any changed, then it's changed
            #  if changed, add group key to groups_changed list so that we can notify signal
            #  Keep track of each medium state change True -> False, False -> True, None -> True, None -> False,
            #  True -> None, False -> None, return list of groups an within that list of changes, with each change
            #  containing the medium, prev state, next state

        super().save(**kwargs)

        # TODO
        # if changed_message_preference:
        #     message_preferences_changed.send(sender=self.__class__, groups_changed=groups_changed)
