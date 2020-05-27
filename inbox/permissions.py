from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from rest_framework import permissions


User = get_user_model()


class RequestPermissionStateMixin(object):

    name = None

    def __init__(self, name=None, **kwargs):
        super(RequestPermissionStateMixin, self).__init__(**kwargs)

        if name:
            self.name = name

    def __call__(self):
        return self

    def _set_on_request(self, request, has_permission):
        if self.name:
            permissions = getattr(request, 'permissions', {})
            permissions[self.name] = has_permission
            request.permissions = permissions

    def has_permission(self, request, view):
        has_permission = super(RequestPermissionStateMixin, self).has_permission(request, view)

        self._set_on_request(request, has_permission)

        return has_permission

    def has_object_permission(self, request, view, obj):
        has_permission = super(RequestPermissionStateMixin, self).has_object_permission(request, view, obj)

        self._set_on_request(request, has_permission)

        return has_permission


class RequirePassword(RequestPermissionStateMixin, permissions.BasePermission):
    """
    When this permission is added to a view[set] it requires that the
    `password` field also be passed as part of the request, useful for change email/password type requests
    where you want to make sure the request actually has permission.
    """
    def has_permission(self, request, view):
        password = request.data.get('password')
        if not password or not request.user.check_password(password):
            raise PermissionDenied

        return True


class IsAuthenticatedOrReadOnlyOrCreate(RequestPermissionStateMixin, permissions.BasePermission):
    """
    The request is authenticated as a user, or is a read-only request, or non-authenticated create
    """
    def has_permission(self, request, view):
        if (request.method in ['GET', 'HEAD', 'OPTIONS'] or
                (request.user and request.user.is_authenticated()) or
                    request.method == 'POST'):
            return True
        return False


class _IsOwner(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    Assumes the model instance has the attribute specified as attr, otherwise
    it assumes the object itself is a User object to compare to authenticated User.
    """
    def __init__(self, user_attr=None, object_user_attr=None, actions=('create', 'list')):
        self.user_attr = user_attr
        self.object_user_attr = object_user_attr
        self.actions = actions

    def __call__(self):
        return self

    def has_permission(self, request, view):
        has_perm = True
        if view.action and view.action in self.actions:
            user_id = view.kwargs.get(self.user_attr) if self.user_attr else view.kwargs.get('parent_lookup_user')
            has_perm = str(user_id) == str(request.user.pk)

        return has_perm

    def has_object_permission(self, request, view, obj):

        if self.object_user_attr:
            user_or_user_id = getattr(obj, self.object_user_attr)
            if isinstance(user_or_user_id, get_user_model()):
                has_perm = user_or_user_id == request.user
            else:
                has_perm = str(user_or_user_id) == str(request.user.pk)
        else:
            has_perm = obj == request.user

        return has_perm


class IsOwner(RequestPermissionStateMixin, _IsOwner):
    pass
