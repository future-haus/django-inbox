from rest_framework import serializers

from inbox import settings as inbox_settings
from inbox.models import Message, get_message_group

MESSAGE_GROUPS = inbox_settings.get_config()['MESSAGE_GROUPS']


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


class MessageUpdateSerializer(serializers.ModelSerializer):

    is_read = serializers.BooleanField(required=True)

    class Meta:
        model = Message
        fields = ['is_read']
