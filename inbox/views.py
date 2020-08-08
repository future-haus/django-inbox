from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import RetrieveModelMixin, DestroyModelMixin, ListModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_extensions.mixins import NestedViewSetMixin

from inbox.models import Message
from inbox.permissions import IsOwner
from inbox.serializers import MessageSerializer, MessageListSerializer, MessageUpdateSerializer
from inbox.utils import save_message_preferences


class NestedMessagePreferencesMixin:

    @action(methods=['GET', 'PUT'], detail=True,
            url_path='message[-_]preferences(?:/(?P<preference_id>[a-z_]+)/(?P<medium_id>[a-z_]+))?',
            permission_classes=[IsAuthenticated, IsOwner])
    def message_preferences(self, request, pk=None, dash=None, preference_id=None, medium_id=None, **kwargs):
        """
        Mixin for UserViewSet

        Supports updating all preferences at once, eg PUT /api/v1/users/{userId}/message-preferences
        Supports updating a single preference+medium combo, eg PUT /api/v1/users/{userId}/message-preferences/{preferenceId}/{medium}

        :param request:
        :param pk:
        :param args:
        :param kwargs:
        :return:
        """
        message_preferences = self.get_object().message_preferences

        if self.request.method == 'PUT':
            try:
                message_preferences = save_message_preferences(
                    message_preferences,
                    self.request.data if preference_id and medium_id else self.request.data.get('results'),
                    preference_id,
                    medium_id
                )
            except ValueError as e:
                raise ValidationError(e.args)

        if preference_id and medium_id:
            return Response(self.request.data, status=status.HTTP_200_OK)
        else:
            return Response({'results': message_preferences.groups}, status=status.HTTP_200_OK)


class NestedMessagesViewSet(NestedViewSetMixin, ListModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated, IsOwner)
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

    @action(detail=False, methods=['post'])
    def read(self, request, version, parent_lookup_user):
        Message.objects.mark_all_read(user_id=parent_lookup_user)
        return Response(status=200)

    @action(detail=False, methods=['get'], url_path='unread[-_]count',
            permission_classes=(IsAuthenticated, IsOwner(actions='unread_count')))
    def unread_count(self, request, version, parent_lookup_user):
        unread_count = Message.objects.unread_count(parent_lookup_user)
        return Response(status=200, data=unread_count)


class MessageViewSet(RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated, IsOwner(object_user_attr='user'),)
    queryset = Message.objects.all()
    serializer_classes = {
        'retrieve': MessageSerializer,
        'update': MessageUpdateSerializer
    }

    def get_queryset(self):
        now = timezone.now()
        # INFO ordering of the query is important here, aligns with the combined index
        qs = super().get_queryset().filter(send_at__lte=now, is_hidden=False, is_logged=True, deleted_at__isnull=True)
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

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        serializer = MessageSerializer(instance, context=self.get_serializer_context())

        return Response(serializer.data)
