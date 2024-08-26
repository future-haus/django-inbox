import logging

from django.contrib.auth import get_user_model
from django.utils import timezone

from django.conf import settings
from rest_framework import mixins, viewsets, permissions
from rest_framework import status
from rest_framework import validators
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin
import requests

from .models import DeviceGroup
from .serializers import DeviceSerializer, UserSerializer
from inbox.models import Message
from inbox.views import NestedMessagePreferencesMixin

User = get_user_model()


class UserViewSet(
    NestedMessagePreferencesMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def update(self, request, *args, **kwargs):
        # Using this endpoint as a test to trigger an update message that goes to a user's inbox/sent out via email/txt
        response = super().update(request, *args, **kwargs)

        user = self.get_object()
        Message.objects.create(user=user, key="account_updated")

        # Create another in future just so we can test future capability
        future_send_at = timezone.now() + timezone.timedelta(days=2)
        Message.objects.create(user=user, key="account_updated", send_at=future_send_at)

        return response


class UserDeviceViewSet(
    NestedViewSetMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    queryset = DeviceGroup.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def create(self, request, *args, **kwargs):
        request.data["user"] = request.user
        return super(UserDeviceViewSet, self).create(request, *args, **kwargs)


class DeviceViewSet(mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = DeviceSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def destroy(self, request, pk, *args, **kwargs):
        # Look up device_group for user to do the removal
        device_group = request.user.device_group

        from inbox.core.app_push.backends.firebase import AppPushBackend

        backend = AppPushBackend()
        headers = {
            "project_id": settings.GOOGLE_FCM_SENDER_ID,
        }
        headers.update(backend.fcm.request_headers())

        # DeviceGroup will only have notification_key if previously saved to Google, make this an add operation
        if device_group.notification_key:
            data = {
                "operation": "remove",
                "notification_key_name": device_group.notification_key_name,
                "registration_ids": [pk],
            }

            if device_group.notification_key == "FORGOT":
                headers["Content-Type"] = "application/json"
                response = requests.get(
                    "https://fcm.googleapis.com/fcm/notification",
                    headers=headers,
                    params={
                        "notification_key_name": device_group.notification_key_name
                    },
                )
                device_group.notification_key = response.json()["notification_key"]

            data.update(notification_key=device_group.notification_key)

            response = requests.post(
                "https://fcm.googleapis.com/fcm/notification",
                headers=headers,
                json=data,
            )
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if (
            response.status_code == 400
            and response.json().get("error") == "notification_key not found"
        ):
            device_group.delete()
        elif response.status_code >= 400:
            logging.debug(response.status_code)
            logging.debug(response.content)
            raise validators.ValidationError({"device": "invalid"})

        return Response(status=status.HTTP_204_NO_CONTENT)
