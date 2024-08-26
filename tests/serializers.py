from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers, validators
from rest_framework.serializers import ModelSerializer
import requests

from .models import DeviceGroup

User = get_user_model()


class DeviceSerializer(ModelSerializer):
    registration_token = serializers.CharField(write_only=True)

    class Meta:
        model = DeviceGroup
        fields = ('registration_token',)

    def create(self, validated_data):
        created = True
        device_group = self.initial_data['user'].device_group

        data = {
            'operation': 'create',
            'notification_key_name': device_group.notification_key_name,
            'registration_ids': [validated_data['registration_token']]
        }

        from inbox.core.app_push.backends.firebase import AppPushBackend
        backend = AppPushBackend()
        headers = {
            'project_id': settings.GOOGLE_FCM_SENDER_ID,
        }
        headers.update(backend.fcm.request_headers())

        # DeviceGroup will only have notification_key if previously saved to Google, make this an add operation
        if device_group.notification_key:
            data.update(operation='add')
            if device_group.notification_key == 'FORGOT':
                headers['Content-Type'] = 'application/json'
                response = requests.get('https://fcm.googleapis.com/fcm/notification', headers=headers, params={
                    'notification_key_name': device_group.notification_key_name
                })
                device_group.notification_key = response.json()['notification_key']
            else:
                created = False

            data.update(notification_key=device_group.notification_key)

        response = requests.post("https://fcm.googleapis.com/fcm/notification", headers=headers, json=data)

        already_exists = False
        if response.status_code == 400 and response.json()['error'] == 'notification_key already exists':
            response = requests.get("https://fcm.googleapis.com/fcm/notification", headers=headers,
                                    params={'notification_key_name': device_group.notification_key_name})
            already_exists = True

        if response.status_code == 400 and response.json()['error'] == 'notification_key not found':
            created = True
            data.update(operation='create')
            response = requests.post("https://fcm.googleapis.com/fcm/notification", headers=headers, json=data)

        if not already_exists and response.status_code >= 400:
            raise validators.ValidationError({'device': 'invalid'})

        if already_exists or created:
            return super(DeviceSerializer, self).update(device_group,
                                                        {'notification_key': response.json()['notification_key']})
        else:
            return device_group


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'device_group',)
