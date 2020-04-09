from rest_framework import serializers

from inbox import settings as inbox_settings
from inbox.models import Message, MessagePreferences

MESSAGE_GROUPS = inbox_settings.get_config()['MESSAGE_GROUPS']


class MessagePreferenceSerializer(serializers.Serializer):

    app_push = serializers.NullBooleanField()
    email = serializers.NullBooleanField()
    sms = serializers.NullBooleanField()
    web_push = serializers.NullBooleanField()


class MessagePreferencesSerializer(serializers.ModelSerializer):

    groups = MessagePreferenceSerializer(many=True)

    class Meta:
        model = MessagePreferences
        fields = ['groups']


class MessageListSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(source='send_at')

    class Meta:
        model = Message
        fields = ['id', 'subject', 'body', 'data', 'group', 'is_read', 'created_at']


class MessageSerializer(MessageListSerializer):

    class Meta:
        model = MessageListSerializer.Meta.model
        fields = MessageListSerializer.Meta.fields + []
