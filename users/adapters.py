from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import Firma


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = sociallogin.user

        if not user.firma_id:
            email = user.email or ''
            firma_adi = email.split('@')[0] if email else user.username
            firma = Firma.objects.create(ad=firma_adi)
            user.firma = firma
            user.firma_sahibi_mi = True

        return super().save_user(request, sociallogin, form)
