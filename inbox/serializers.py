from rest_framework import serializers

from inbox import settings as inbox_settings
from inbox.models import Message

MESSAGE_GROUPS = inbox_settings.get_config()['MESSAGE_GROUPS']


class MessageListSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(source='send_at')

    class Meta:
        model = Message
        fields = ['id', 'key', 'subject', 'body', 'data', 'group', 'is_read', 'created_at']


class MessageSerializer(MessageListSerializer):

    body = serializers.SerializerMethodField()

    class Meta:
        model = MessageListSerializer.Meta.model
        fields = MessageListSerializer.Meta.fields + []

    def get_body(self, obj):
        return obj.body_full


class MessageUpdateSerializer(serializers.ModelSerializer):

    is_read = serializers.BooleanField(required=True)

    class Meta:
        model = Message
        fields = ['is_read']
