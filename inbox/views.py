from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import RetrieveModelMixin, DestroyModelMixin, ListModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_extensions.mixins import NestedViewSetMixin

from inbox.constants import MessageMedium
from inbox.models import Message, MessagePreferences, get_default_preference_ids
from inbox.permissions import IsOwner
from inbox.serializers import MessageSerializer, MessageListSerializer, MessageUpdateSerializer


class NestedMessagePreferencesMixin:

    @action(methods=['GET', 'PUT'], detail=True,
            url_path='message_preferences(?:/(?P<preference_id>[a-z_]+)/(?P<medium_id>[a-z_]+))?',
            permission_classes=[IsAuthenticated, IsOwner])
    def message_preferences(self, request, pk=None, preference_id=None, medium_id=None, **kwargs):
        """
        Mixin for UserViewSet

        Supports updating all preferences at once, eg PUT /api/v1/users/{userId}/message_preferences
        Supports updating a single preference+medium combo, eg PUT /api/v1/users/{userId}/message_preferences/{preferenceId}/{medium}

        :param request:
        :param pk:
        :param args:
        :param kwargs:
        :return:
        """
        message_preferences = self.get_object().message_preferences

        is_single = False
        if self.request.method == 'PUT':
            if preference_id and preference_id not in get_default_preference_ids():
                raise ValidationError(
                    {'preference_id': [f'The preference_id ({preference_id}) specified in the path is invalid.']}
                )
            if medium_id and MessageMedium.get(medium_id.upper()) is None:
                raise ValidationError(
                    {'medium_id': [f'The medium_id ({medium_id}) specified in the path is invalid.']}
                )
            if preference_id and medium_id:
                is_single = True

                message_preferences = MessagePreferences.objects.select_for_update().get(pk=message_preferences.pk)
                for k, group in enumerate(message_preferences._groups):
                    if group['id'] == preference_id:
                        message_preferences._groups[k][medium_id] = self.request.data
                        break
            elif self.request.data.get('results'):
                message_preferences.groups = self.request.data['results']

            message_preferences.save()

        if is_single:
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

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        serializer = MessageSerializer(instance, context=self.get_serializer_context())

        return Response(serializer.data)
