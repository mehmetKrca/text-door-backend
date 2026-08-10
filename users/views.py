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
import datetime

from .models import AbonelikPaketi, Proje, SepetKalemi, FiyatTablosu, Firma 

from .serializers import (
    UserRegisterSerializer, 
    AbonelikPaketiSerializer, 
    CalisanEkleSerializer, 
    ProjeKaydetSerializer
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
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def create(self, request, *args, **kwargs):
        patron = request.user

        if not patron.firma_sahibi_mi:
            return Response({"error": "Bu işlemi sadece firma sahibi yapabilir."}, status=403)

        paket = patron.firma.paket
        if not paket or not paket.sinirsiz_kullanici:
            limit = paket.max_kullanici if paket else 1
            mevcut_kullanici_sayisi = patron.firma.calisanlar.count()
            if mevcut_kullanici_sayisi >= limit:
                return Response({"error": "Paketinizin kullanıcı limitine ulaşıldı."}, status=400)

        return super().create(request, *args, **kwargs)

# BAYİNİN PROJEYİ BULUTA KAYDEDECEĞİ API UCU
class ProjeCreateView(generics.CreateAPIView):
    queryset = Proje.objects.all()
    serializer_class = ProjeKaydetSerializer
    permission_classes = [IsAuthenticated] 
    throttle_classes = [UserRateThrottle]

# ==============================================================
# 🛡️ YENİ EKLENEN PROFİL İŞLEMLERİ (404 HATASINI ÇÖZEN VİEW'LAR)
# ==============================================================

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        user = request.user
        firma_adi = user.firma.ad if getattr(user, 'firma', None) else None
        telefon = getattr(user, 'telefon', '')

        return Response({
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'telefon': telefon,
            'firma_adi': firma_adi,
        })

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
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([UserRateThrottle])
def projeleri_getir(request):
    firma = request.user.firma
    projeler = Proje.objects.filter(kullanici__firma=firma).order_by('-id')

    data = []
    for proje in projeler:
        kalemler = SepetKalemi.objects.filter(proje=proje)
        sepet_listesi = []
        for k in kalemler:
            tam_item = k.detaylar if isinstance(k.detaylar, dict) else {}
            tam_item['id'] = k.id
            tam_item['isim'] = k.isim
            tam_item['urunTipi'] = k.urun_tipi
            tam_item['genislik'] = k.genislik
            tam_item['yukseklik'] = k.yukseklik
            tam_item['fiyat'] = float(k.fiyat)
            sepet_listesi.append(tam_item)

        data.append({
            'id': proje.id,
            'projeAdi': proje.proje_adi,
            'musteriTel': proje.musteri_tel,
            'teklifTarihi': proje.teklif_tarihi,
            'durum': getattr(proje, 'durum', 'teklif') or 'teklif',
            'toplamFiyat': float(proje.toplam_fiyat),
            'sepet': sepet_listesi
        })
        
    return JsonResponse(data, safe=False)

# ==============================================================
# 🎯 KALICI FİYAT TABLOSU GETİRME VE GÜNCELLEME APİ'Sİ
# ==============================================================
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
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