from rest_framework.permissions import BasePermission


class IsPatron(BasePermission):
    """Sadece rolü 'patron' olan kullanicilara izin verir."""
    message = "Bu işlemi sadece firma sahibi (patron) yapabilir."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'rol', None) == 'patron'
        )
