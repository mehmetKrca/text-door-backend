from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView 
from .views import (
    RegisterView, 
    PaketListView, 
    CalisanEkleView, 
    ProjeCreateView, 
    projeleri_getir, 
    fiyat_tablosu_api,
    CustomGoogleLoginView,
    abonelik_durumu,
    abonelik_baslat,
    proje_durum_guncelle,
    proje_sil,
    CurrentUserView,        # YENİ EKLENDİ
    ProfileUpdateView,      # YENİ EKLENDİ
    PasswordChangeView,     # YENİ EKLENDİ
    KullaniciIstatistikleri,
    HesapDondurView,
    HesapSilView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('google/', CustomGoogleLoginView.as_view(), name='google_login'),
    path('packages/', PaketListView.as_view(), name='paket-listesi'),
    path('calisan-ekle/', CalisanEkleView.as_view(), name='calisan-ekle'),
    path('fiyat-tablosu/', fiyat_tablosu_api, name='fiyat-tablosu'),
    path('proje-kaydet/', ProjeCreateView.as_view(), name='proje-kaydet'),
    path('projeleri-getir/', projeleri_getir, name='projeleri-getir'),
    
    # 🎯 CRM DURUM GÜNCELLEME ENDPOINT'İ
    path('proje-durum-guncelle/<int:proje_id>/', proje_durum_guncelle, name='proje-durum-guncelle'),
    path('proje-sil/<int:proje_id>/', proje_sil, name='proje-sil'),

    # 🎯 YENİ: PROFİL İŞLEMLERİ (404 HATALARINI ÇÖZEN KISIM)
    path('me/', CurrentUserView.as_view(), name='current-user'),
    path('profile-update/', ProfileUpdateView.as_view(), name='profile-update'),
    path('password-change/', PasswordChangeView.as_view(), name='password-change'),

    # ABONELİK & PAYWALL ENDPOINT'LERİ
    path('abonelik-durumu/', abonelik_durumu, name='abonelik-durumu'),
    path('abonelik-baslat/', abonelik_baslat, name='abonelik-baslat'),

    # 🎯 PROFİL EKRANI: İSTATİSTİKLER, HESAP DONDURMA VE HESAP SİLME
    path('istatistikler/', KullaniciIstatistikleri.as_view(), name='istatistikler'),
    path('hesap-dondur/', HesapDondurView.as_view(), name='hesap-dondur'),
    path('hesap-sil/', HesapSilView.as_view(), name='hesap-sil'),
]