from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Standart Giriş / Çıkış ve Token işlemleri (Bozulmasın diye duruyor)
    path('api/auth/', include('dj_rest_auth.urls')),
    
    # Yeni kullanıcı kayıt işlemleri
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    
    # Google giriş ve sosyal hesaplar için şart olan allauth yolları
    path('accounts/', include('allauth.urls')),
    
    # --- İŞTE 404 HATASINI BİTİREN KRİTİK KÖPRÜ ---
    # React'in istek attığı /api/users/register/ adresini yakalayan yer burası
    path('api/users/', include('users.urls')),
]