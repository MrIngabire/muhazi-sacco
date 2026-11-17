# backend/core/permissions.py — NEW FILE

from functools import wraps
from rest_framework.response import Response
from .models import Role


def require_role(*allowed_roles):
    """Decorator: require the requesting user to have one of these roles."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            try:
                role = Role.objects.get(user=request.user)
            except Role.DoesNotExist:
                return Response({'error': 'No role assigned'}, status=403)
            if role.role not in allowed_roles:
                return Response({
                    'error': f'This action requires one of: {", ".join(allowed_roles)}'
                }, status=403)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_permission(permission_name):
    """Decorator: require a specific boolean permission on Role."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            try:
                role = Role.objects.get(user=request.user)
            except Role.DoesNotExist:
                return Response({'error': 'No role assigned'}, status=403)
            if not getattr(role, permission_name, False):
                return Response({
                    'error': f'Missing permission: {permission_name}'
                }, status=403)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator