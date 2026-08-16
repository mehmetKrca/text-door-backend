from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin

# Allauth ve çöp modülleri güvenli bir şekilde gizliyoruz
try:
    from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
    from allauth.account.models import EmailAddress
    from django.contrib.sites.models import Site
    admin.site.unregister(Group)
    admin.site.unregister(SocialAccount)
    admin.site.unregister(SocialApp)
    admin.site.unregister(SocialToken)
    admin.site.unregister(EmailAddress)
    admin.site.unregister(Site)
except Exception:
    pass

# Senin gerçek modellerin
from .models import AbonelikPaketi, Firma, CustomUser, FiyatTablosu, Proje, SepetKalemi, HesapSilmeTalebi

@admin.register(AbonelikPaketi)
class AbonelikPaketiAdmin(admin.ModelAdmin):
    list_display = ('ad', 'periyot', 'fiyat', 'sinirsiz_kullanici', 'max_kullanici')
    search_fields = ('ad',)

class FirmaAdminForm(forms.ModelForm):
    class Meta:
        model = Firma
        fields = '__all__'
        help_texts = {
            'abonelik_bitis': "Tek seferlik ödemede boş bırakın, ömür boyu geçerli olur.",
        }

@admin.register(Firma)
class FirmaAdmin(admin.ModelAdmin):
    form = FirmaAdminForm
    list_display = ('ad', 'paket', 'abonelik_periyot', 'telefon', 'abonelik_baslangic', 'abonelik_bitis')
    search_fields = ('ad', 'telefon')
    list_filter = ('paket', 'abonelik_periyot')

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'firma', 'firma_sahibi_mi', 'telefon', 'is_staff')
    search_fields = ('username', 'email', 'telefon', 'firma__ad')
    list_filter = ('firma_sahibi_mi', 'is_staff', 'firma')
    # CustomUser içinde ekstra alanlar olduğu için admin panelinde form alanlarını genişletiyoruz
    fieldsets = UserAdmin.fieldsets + (
        ('Firma ve Ek Bilgiler', {'fields': ('firma', 'telefon', 'firma_sahibi_mi')}),
    )

@admin.register(FiyatTablosu)
class FiyatTablosuAdmin(admin.ModelAdmin):
    list_display = ('firma', 'guncellenme_tarihi')
    search_fields = ('firma__ad',)

class SepetKalemiInline(admin.TabularInline):
    model = SepetKalemi
    extra = 0

@admin.register(Proje)
class ProjeAdmin(admin.ModelAdmin):
    list_display = ('proje_adi', 'kullanici', 'musteri_tel', 'toplam_fiyat', 'olusturulma_tarihi')
    search_fields = ('proje_adi', 'musteri_tel', 'kullanici__username')
    list_filter = ('teklif_tarihi',)
    inlines = [SepetKalemiInline]

@admin.register(SepetKalemi)
class SepetKalemiAdmin(admin.ModelAdmin):
    list_display = ('proje', 'isim', 'urun_tipi', 'genislik', 'yukseklik', 'fiyat')
    search_fields = ('isim', 'urun_tipi', 'proje__proje_adi')

@admin.register(HesapSilmeTalebi)
class HesapSilmeTalebiAdmin(admin.ModelAdmin):
    list_display = ('email', 'olusturma_tarihi', 'islendi_mi')
    list_filter = ('islendi_mi',)
    search_fields = ('email', 'aciklama')