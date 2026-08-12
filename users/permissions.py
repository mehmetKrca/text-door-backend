from rest_framework.permissions import BasePermission
from rest_framework.exceptions import APIException
from rest_framework import status


class IsPatron(BasePermission):
    """Sadece rolü 'patron' olan kullanicilara izin verir."""
    message = "Bu işlemi sadece firma sahibi (patron) yapabilir."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'rol', None) == 'patron'
        )


class PaymentRequired(APIException):
    """Abonelik/deneme süresi dolduğunda veya hesap donduğunda 402 dönmek için."""
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = "Aboneliğinizin süresi dolmuş veya hesabınız donduruldu. Lütfen aboneliğinizi yenileyin."
    default_code = "payment_required"


class AbonelikAktif(BasePermission):
    """
    request.user.firma.erisim_izni_var_mi False ise 402 Payment Required döner.
    (Deneme süresi dolmuş, ödemeli abonelik bitmiş veya hesap donduruşmuş olabilir.)
    """
    message = PaymentRequired.default_detail

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        firma = getattr(request.user, 'firma', None)

        if not firma or not firma.erisim_izni_var_mi:
            raise PaymentRequired()

        return True
