from django.http import JsonResponse

class PaywallMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Sadece giriş yapmış kullanıcılar için kontrol et
        if request.user.is_authenticated:
            # Ödeme yapma API'si veya profil endpoints hariç tutulsun ki ödeme yapabilsin!
            muaf_urller = ['/api/users/odeme-yap/', '/api/users/profil/', '/admin/']
            
            if not any(request.path.startswith(url) for url in muaf_urller):
                if not request.user.erisim_izni_var_mi:
                    return JsonResponse({
                        'error': 'PAYWALL_BLOCKED',
                        'detail': '14 günlük ücretsiz deneme süreniz dolmuştur. Lütfen devam etmek için aboneliğinizi başlatın.',
                        'kalan_gun': 0
                    }, status=402)  # 402 Payment Required

        response = self.get_response(request)
        return response