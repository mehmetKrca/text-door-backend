from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.throttling import ScopedRateThrottle, AnonRateThrottle, UserRateThrottle
from rest_framework.response import Response
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from django.db import transaction
import datetime
import re

from .models import AbonelikPaketi, Proje, SepetKalemi, FiyatTablosu, Firma, HesapSilmeTalebi
from .permissions import IsPatron, AbonelikAktif

from .serializers import (
    UserRegisterSerializer,
    AbonelikPaketiSerializer,
    CalisanEkleSerializer,
    ProjeKaydetSerializer,
    CurrentUserSerializer
)

# --- GOOGLE İLE GİRİŞ İÇİN KÜTÜPHANELER ---
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

User = get_user_model()

# ==============================================================
# 🚀 KAYIT VE PAKET APİ UÇLARI
# ==============================================================
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserRegisterSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

class PaketListView(generics.ListAPIView):
    queryset = AbonelikPaketi.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = AbonelikPaketiSerializer
    throttle_classes = [AnonRateThrottle, UserRateThrottle]

# Patronun eleman ekleyeceği güvenli API ucu
class CalisanEkleView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = CalisanEkleSerializer
    permission_classes = [IsAuthenticated, IsPatron, AbonelikAktif]
    throttle_classes = [UserRateThrottle]

    def create(self, request, *args, **kwargs):
        patron = request.user

        if getattr(patron, 'rol', None) != 'patron':
            return Response({"error": "Bu işlemi sadece firma sahibi yapabilir."}, status=403)

        paket = patron.firma.paket
        if not paket or not paket.sinirsiz_kullanici:
            limit = paket.max_kullanici if paket else 1
            mevcut_kullanici_sayisi = patron.firma.calisanlar.exclude(pk=patron.pk).count()
            if mevcut_kullanici_sayisi >= limit:
                return Response({"error": "Paketinizin kullanıcı limitine ulaşıldı."}, status=400)

        return super().create(request, *args, **kwargs)

# BAYİNİN PROJEYİ BULUTA KAYDEDECEĞİ API UCU
class ProjeCreateView(generics.CreateAPIView):
    queryset = Proje.objects.all()
    serializer_class = ProjeKaydetSerializer
    permission_classes = [IsAuthenticated, AbonelikAktif]
    throttle_classes = [UserRateThrottle]

# ==============================================================
# 🛡️ YENİ EKLENEN PROFİL İŞLEMLERİ (404 HATASINI ÇÖZEN VİEW'LAR)
# ==============================================================

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        serializer = CurrentUserSerializer(request.user)
        return Response(serializer.data)

class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def patch(self, request):
        user = request.user
        data = request.data
        
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.email = data.get('email', user.email)
        
        if hasattr(user, 'telefon'):
            user.telefon = data.get('telefon', getattr(user, 'telefon', ''))
            
        firma_adi = data.get('firma_adi')
        if firma_adi:
            if getattr(user, 'firma', None):
                user.firma.ad = firma_adi
                user.firma.save()
            else:
                yeni_firma, _ = Firma.objects.get_or_create(ad=firma_adi)
                user.firma = yeni_firma
                
        user.save()
        return Response({"message": "Profil başarıyla güncellendi!"}, status=200)

class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not new_password:
            return Response({"error": "Yeni şifre boş olamaz."}, status=400)

        if not user.check_password(old_password):
            return Response({"error": "Mevcut şifrenizi yanlış girdiniz."}, status=400)

        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as e:
            return Response({"error": e.messages}, status=400)

        user.set_password(new_password)
        user.save()
        return Response({"message": "Şifreniz başarıyla güncellendi."}, status=200)

# ==============================================================
# 🛡️ MÜŞTERİ ARŞİVİ (TAM FİRMA İZOLASYONU İLE VERİ KARIŞMASI ENGELLENDİ)
# ==============================================================
_FIYAT_ANAHTAR_RE = re.compile(r'fiyat|price|tl$', re.IGNORECASE)


def _fiyat_alani_mi(anahtar):
    return bool(_FIYAT_ANAHTAR_RE.search(anahtar))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([UserRateThrottle])
def projeleri_getir(request):
    firma = request.user.firma
    usta_mi = getattr(request.user, 'rol', None) == 'usta'
    projeler = Proje.objects.filter(kullanici__firma=firma).order_by('-id')

    data = []
    for proje in projeler:
        kalemler = SepetKalemi.objects.filter(proje=proje)
        sepet_listesi = []
        for k in kalemler:
            kaynak_detay = k.detaylar if isinstance(k.detaylar, dict) else {}
            if usta_mi:
                tam_item = {
                    anahtar: deger for anahtar, deger in kaynak_detay.items()
                    if not _fiyat_alani_mi(anahtar)
                }
            else:
                tam_item = dict(kaynak_detay)

            tam_item['id'] = k.id
            tam_item['isim'] = k.isim
            tam_item['urunTipi'] = k.urun_tipi
            tam_item['genislik'] = k.genislik
            tam_item['yukseklik'] = k.yukseklik
            if not usta_mi:
                tam_item['fiyat'] = float(k.fiyat)
            sepet_listesi.append(tam_item)

        proje_verisi = {
            'id': proje.id,
            'projeAdi': proje.proje_adi,
            'musteriTel': proje.musteri_tel,
            'teklifTarihi': proje.teklif_tarihi,
            'durum': getattr(proje, 'durum', 'teklif') or 'teklif',
            'sepet': sepet_listesi
        }
        if not usta_mi:
            proje_verisi['toplamFiyat'] = float(proje.toplam_fiyat)

        data.append(proje_verisi)

    return JsonResponse(data, safe=False)

# ==============================================================
# 🎯 KALICI FİYAT TABLOSU GETİRME VE GÜNCELLEME APİ'Sİ
# ==============================================================
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsPatron])
@throttle_classes([UserRateThrottle])
def fiyat_tablosu_api(request):
    user = request.user

    if request.method == 'GET':
        firma = user.firma

        if firma:
            fiyat_tablosu, _ = FiyatTablosu.objects.get_or_create(firma=firma)
            veri = getattr(fiyat_tablosu, 'fiyatlar', None) or getattr(fiyat_tablosu, 'veri', {}) or {}
            return Response({'status': 'success', 'veri': veri, **veri})
        else:
            return Response({})

    if request.method == 'POST':
        AbonelikAktif().has_permission(request, None)

        firma = user.firma
        if not firma:
            firma, _ = Firma.objects.get_or_create(ad=f"{user.username} Atölyesi")
            user.firma = firma
            user.save()

        fiyat_tablosu, _ = FiyatTablosu.objects.get_or_create(firma=firma)
        
        if hasattr(fiyat_tablosu, 'fiyatlar'):
            fiyat_tablosu.fiyatlar = request.data
        else:
            fiyat_tablosu.veri = request.data
            
        fiyat_tablosu.save()
        return Response({
            'message': 'Fiyatlar veritabanına başarıyla sabitlendi! 🚀',
            'veri': request.data
        }, status=200)

# ==============================================================
# ABONELİK BİLGİSİ SORGULAMA VE BAŞLATMA
# ==============================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([UserRateThrottle])
def abonelik_durumu(request):
    user = request.user
    firma = user.firma
    if not firma:
        firma, _ = Firma.objects.get_or_create(ad=f"{user.username} Atölyesi")
        user.firma = firma
        user.save()

    return Response({
        'erisim_izni': getattr(firma, 'erisim_izni_var_mi', True),
        'abonelik_aktif': getattr(firma, 'abonelik_aktif', False),
        'kalan_deneme_gunu': getattr(firma, 'kalan_deneme_gunu', 14),
        'deneme_doldu_mu': getattr(firma, 'deneme_suresi_doldu_mu', False),
        'abonelik_bitis': getattr(firma, 'abonelik_bitis', None)
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsPatron])
@throttle_classes([UserRateThrottle])
def abonelik_baslat(request):
    firma = getattr(request.user, 'firma', None)
    if not firma:
        firma, _ = Firma.objects.get_or_create(ad=f"{request.user.username} Atölyesi")
        request.user.firma = firma
        request.user.save()

    paket_periyot = request.data.get('periyot', 'Aylık')
    
    firma.abonelik_aktif = True
    if paket_periyot == 'Yıllık':
        firma.abonelik_bitis = timezone.now() + datetime.timedelta(days=365)
    else:
        firma.abonelik_bitis = timezone.now() + datetime.timedelta(days=30)
        
    firma.save()
    
    return Response({
        'status': 'success',
        'message': 'eWindoore Premium aboneliğiniz başarıyla başlatıldı! 🚀',
        'erisim_izni': True,
        'abonelik_aktif': True,
        'abonelik_bitis': firma.abonelik_bitis
    })

# GOOGLE İLE GİRİŞ VIEW'I
class CustomGoogleLoginView(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    callback_url = "http://localhost:5173"
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

# ==============================================================
# 🎯 CRM PROJE DURUMU GÜNCELLEME API UCU
# ==============================================================
@api_view(['PATCH', 'PUT', 'POST'])
@permission_classes([IsAuthenticated, AbonelikAktif])
@throttle_classes([UserRateThrottle])
def proje_durum_guncelle(request, proje_id):
    try:
        yeni_durum = request.data.get('durum')
        if not yeni_durum:
            return Response({'error': 'Yeni durum belirtilmedi.'}, status=400)

        proje = Proje.objects.filter(id=proje_id, kullanici__firma=request.user.firma).first()
        
        if proje:
            proje.durum = yeni_durum
            proje.save()
            return Response({'status': 'success', 'message': f'Durum "{yeni_durum}" veritabanına kaydedildi!'}, status=200)
        else:
            return Response({'status': 'error', 'message': 'Proje bulunamadı veya yetkiniz yok.'}, status=404)
            
    except Exception as e:
        return Response({'error': str(e)}, status=500)

# ==============================================================
# 🎯 CRM PROJE SİLME API UCU
# ==============================================================
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@throttle_classes([UserRateThrottle])
def proje_sil(request, proje_id):
    proje = Proje.objects.filter(id=proje_id, kullanici__firma=request.user.firma).first()

    if not proje:
        return Response({'status': 'error', 'message': 'Proje bulunamadı veya yetkiniz yok.'}, status=404)

    proje.delete()
    return Response({'status': 'success', 'message': 'Proje silindi.'}, status=200)

# ==============================================================
# 👤 PROFİL EKRANI: İSTATİSTİKLER, HESAP DONDURMA VE HESAP SİLME
# ==============================================================
class KullaniciIstatistikleri(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        firma = request.user.firma

        projeler = Proje.objects.filter(kullanici__firma=firma)

        return Response({
            'proje_sayisi': projeler.count(),
            'cizim_sayisi': SepetKalemi.objects.filter(proje__kullanici__firma=firma).count(),
            'teklif_sayisi': projeler.filter(durum='teklif').count(),
            'calisan_sayisi': firma.calisanlar.count() if firma else 0,
        })


class HesapDondurView(APIView):
    permission_classes = [IsAuthenticated, IsPatron]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        firma = request.user.firma
        if not firma:
            return Response({"error": "Firma bulunamadı."}, status=400)

        firma.abonelik_donduruldu = not firma.abonelik_donduruldu
        firma.dondurma_tarihi = timezone.now() if firma.abonelik_donduruldu else None
        firma.save()

        if firma.abonelik_donduruldu:
            return Response({
                'status': 'success',
                'message': 'Hesabınız donduruldu.',
                'abonelik_donduruldu': True,
                'dondurma_tarihi': firma.dondurma_tarihi
            })
        else:
            return Response({
                'status': 'success',
                'message': 'Hesap dondurma kaldırıldı.',
                'abonelik_donduruldu': False,
                'dondurma_tarihi': None
            })


class HesapSilView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        user = request.user
        firma = user.firma

        girilen_firma_adi = request.data.get('firma_adi')

        if not girilen_firma_adi or not str(girilen_firma_adi).strip():
            return Response({"error": "Firma adı boş olamaz."}, status=400)

        gercek_firma_adi = firma.ad if firma else None

        if not gercek_firma_adi or girilen_firma_adi != gercek_firma_adi:
            return Response({"error": "Firma adı doğrulanamadı."}, status=400)

        if getattr(user, 'rol', None) == 'patron':
            with transaction.atomic():
                SepetKalemi.objects.filter(proje__kullanici__firma=firma).delete()
                Proje.objects.filter(kullanici__firma=firma).delete()
                FiyatTablosu.objects.filter(firma=firma).delete()
                User.objects.filter(firma=firma).delete()
                Firma.objects.filter(id=firma.id).delete()

            return Response({
                'status': 'success',
                'message': 'Firma ve tüm verileri kalıcı olarak silindi.'
            })
        else:
            user.delete()
            return Response({
                'status': 'success',
                'message': 'Hesabınız kalıcı olarak silindi.'
            })

# ==============================================================
# 👥 PATRON: ÇALIŞAN LİSTESİ VE ÇALIŞAN SİLME
# ==============================================================
class CalisanListesiView(APIView):
    permission_classes = [IsAuthenticated, IsPatron]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        firma = request.user.firma
        calisanlar = firma.calisanlar.all().order_by('id') if firma else User.objects.none()

        data = [{
            'id': c.id,
            'username': c.username,
            'first_name': c.first_name,
            'last_name': c.last_name,
            'email': c.email,
            'telefon': c.telefon,
            'rol': c.rol,
        } for c in calisanlar]

        return Response(data)


class CalisanSilView(APIView):
    permission_classes = [IsAuthenticated, IsPatron]
    throttle_classes = [UserRateThrottle]

    def delete(self, request, user_id):
        patron = request.user
        hedef = User.objects.filter(id=user_id, firma=patron.firma).first()

        if not hedef:
            return Response({'status': 'error', 'message': 'Kullanıcı bulunamadı veya yetkiniz yok.'}, status=404)

        if hedef.id == patron.id:
            return Response({'status': 'error', 'message': 'Kendi hesabınızı bu ekrandan silemezsiniz, hesap silme işlemini profil ekranından yapınız.'}, status=400)

        with transaction.atomic():
            Proje.objects.filter(kullanici=hedef).update(kullanici=patron)
            hedef.delete()

        return Response({'status': 'success', 'message': 'Çalışan silindi.'}, status=200)

# ==============================================================
# 🗑️ GOOGLE PLAY ZORUNLULUĞU: WEB ÜZERİNDEN HESAP SİLME TALEBİ
# ==============================================================
class HesapSilmeTalebiView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        email = request.data.get('email')
        aciklama = request.data.get('aciklama', '')

        if not email or not str(email).strip():
            return Response({'error': 'E-posta adresi zorunludur.'}, status=400)

        HesapSilmeTalebi.objects.create(email=str(email).strip(), aciklama=aciklama)

        return Response({
            'status': 'success',
            'message': 'Hesap silme talebiniz alındı. En kısa sürede işleme alınacaktır.'
        }, status=201)