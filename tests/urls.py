from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include

from inbox.cron import view_process_new_messages
from inbox.views import MessageViewSet, NestedMessagesViewSet
from rest_framework_extensions.routers import ExtendedSimpleRouter

from tests.views import UserViewSet, UserDeviceViewSet, DeviceViewSet

urlpatterns = []

router = ExtendedSimpleRouter(trailing_slash=False)
router.register(r'devices', DeviceViewSet, basename='devices')
users_router = router.register(r'users', UserViewSet)
users_router.register(r'devices', UserDeviceViewSet,
                      basename='users_devices', parents_query_lookups=['user'])
users_router.register(r'messages', NestedMessagesViewSet, basename='users_messages', parents_query_lookups=['user'])

messages_router = router.register(r'messages', MessageViewSet, basename='messages')

urlpatterns = [
    url(r'^api/(?P<version>v1)/', include(router.urls)),
    url(r'^cron/process_new_messages$', view_process_new_messages),
]

urlpatterns += staticfiles_urlpatterns()
