from annoying.fields import AutoOneToOneField
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.db import models
from hashids import Hashids

User = get_user_model()


class DeviceGroup(models.Model):

    user = AutoOneToOneField(User, related_name='device_group', on_delete=models.CASCADE)
    notification_key = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.notification_key_name

    @property
    def notification_key_name(self):
        hashids = Hashids(salt=settings.SECRET_KEY)
        value = hashids.encode(self.user_id)
        return value


def get_notification_key(entity: User):
    return entity.device_group.notification_key
