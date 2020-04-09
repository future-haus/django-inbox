from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.mixins import RetrieveModelMixin, DestroyModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_extensions.mixins import NestedViewSetMixin

from inbox.models import Message
from inbox.permissions import IsOwner
from inbox.serializers import MessageSerializer, MessageListSerializer


class NestedMessagePreferencesMixin:

    @action(methods=['GET', 'PUT'], detail=True, permission_classes=[IsAuthenticated, IsOwner])
    def message_preferences(self, request, pk=None, *args, **kwargs):
        message_preferences = self.get_object().message_preferences

        if self.request.method == 'PUT':
            message_preferences.groups = self.request.data['groups']
            message_preferences.save()

        return Response({'groups': message_preferences.groups}, status=status.HTTP_200_OK)


class MessageViewSet(NestedViewSetMixin, RetrieveModelMixin, ListModelMixin, DestroyModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Message.objects.all()
    serializer_classes = {
        'list': MessageListSerializer,
        'retrieve': MessageSerializer
    }

    def get_queryset(self):
        now = timezone.now()
        # INFO ordering of the query is important here, aligns with the combined index
        qs = super().get_queryset().filter(send_at__lte=now, is_hidden=False, deleted_at__isnull=True)
        return qs

    # TODO Move our common lib to a pip repo and use Action serializer
    def get_serializer_class(self):
        if hasattr(self, 'serializer_classes') and isinstance(self.serializer_classes, dict):
            serializer_class = self.serializer_classes.get(self.action)

            if serializer_class:
                return serializer_class

        return super().get_serializer_class()

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=False, methods=['post'])
    def read(self, request, version, parent_lookup_user):
        Message.objects.mark_all_read(user_id=parent_lookup_user)
        return Response(status=200)
