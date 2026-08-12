from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model
from django.utils import timezone
import datetime

# 1. ABONELİK PAKETLERİ
class AbonelikPaketi(models.Model):
    PERIYOT_SECENEKLERI = (
        ('Aylık', 'Aylık'),
        ('Yıllık', 'Yıllık'),
    )
    
    ad = models.CharField(max_length=50, verbose_name="Paket Adı (Örn: Kurumsal Plus)")
    periyot = models.CharField(max_length=10, choices=PERIYOT_SECENEKLERI, default='Aylık', verbose_name="Ödeme Periyodu")
    fiyat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Fiyat (₺)")
    sinirsiz_kullanici = models.BooleanField(default=False, verbose_name="Sınırsız Kullanıcı Hakkı")
    max_kullanici = models.IntegerField(default=1, verbose_name="Maksimum Kullanıcı (Sınırsız değilse)")

    class Meta:
        verbose_name = "Abonelik Paketi"
        verbose_name_plural = "1. Abonelik Paketleri"

    def __str__(self):
        return f"{self.ad} ({self.periyot}) - {self.fiyat} ₺"

# 2. FİRMA PROFİLLERİ (12. GÜN: PAYWALL & 14 GÜNLÜK DENEME EKLENDİ)
class Firma(models.Model):
    ad = models.CharField(max_length=100, verbose_name="Firma / Atölye Adı")
    paket = models.ForeignKey(AbonelikPaketi, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Kullandığı Paket")
    telefon = models.CharField(max_length=15, blank=True, null=True, verbose_name="Firma Telefonu")
    
    # --- 12. GÜN: ABONELİK & DENEME SÜRESİ ALANLARI ---
    DENEME_SURESI_GUN = 14

    abonelik_baslangic = models.DateTimeField(auto_now_add=True, verbose_name="Abonelik/Kayıt Başlangıç")
    abonelik_bitis = models.DateTimeField(blank=True, null=True, verbose_name="Abonelik Bitiş")
    abonelik_aktif = models.BooleanField(default=False, verbose_name="Ödemeli Abonelik Aktif Mi?")

    abonelik_donduruldu = models.BooleanField(default=False, verbose_name="Abonelik Donduruldu Mu?")
    dondurma_tarihi = models.DateTimeField(blank=True, null=True, verbose_name="Dondurma Tarihi")

    class Meta:
        verbose_name = "Firma Profili"
        verbose_name_plural = "2. Müşteri Firmalar"

    def __str__(self):
        return self.ad

    @property
    def deneme_suresi_doldu_mu(self):
        if not self.abonelik_baslangic:
            return False
        bitis_tarihi = self.abonelik_baslangic + datetime.timedelta(days=self.DENEME_SURESI_GUN)
        return timezone.now() > bitis_tarihi

    @property
    def kalan_deneme_gunu(self):
        if not self.abonelik_baslangic:
            return self.DENEME_SURESI_GUN
        bitis_tarihi = self.abonelik_baslangic + datetime.timedelta(days=self.DENEME_SURESI_GUN)
        kalan = (bitis_tarihi - timezone.now()).days
        return max(0, kalan)

    @property
    def erisim_izni_var_mi(self):
        # 0. Hesap dondurulmuşsa (patron tarafından) her şeyden önce erişim kapalı
        if self.abonelik_donduruldu:
            return False

        # 1. Ödemeli aktif abonelik var mı?
        if self.abonelik_aktif:
            if self.abonelik_bitis and timezone.now() > self.abonelik_bitis:
                return False  # Ödenen aboneliğin süresi dolmuş
            return True  # Abonelik sorunsuz devam ediyor
        
        # 2. Ödeme yoksa 14 günlük deneme süresi devam ediyor mu?
        return not self.deneme_suresi_doldu_mu


# 3. KULLANICILAR
class CustomUser(AbstractUser):
    ROL_SECENEKLERI = (
        ('patron', 'Patron'),
        ('usta', 'Usta'),
    )

    firma = models.ForeignKey(Firma, on_delete=models.PROTECT, null=False, blank=False, related_name='calisanlar', verbose_name="Bağlı Olduğu Firma")
    telefon = models.CharField(max_length=15, blank=True, null=True, verbose_name="Kişisel Telefon")
    firma_sahibi_mi = models.BooleanField(default=False, verbose_name="Firma Sahibi Mi?")
    rol = models.CharField(max_length=10, choices=ROL_SECENEKLERI, default='usta', verbose_name="Rol")

    class Meta:
        verbose_name = "Sistem Kullanıcısı"
        verbose_name_plural = "3. Sistem Kullanıcıları"

    def __str__(self):
        if self.firma:
            return f"{self.username} ({self.firma.ad})"
        return self.username

User = get_user_model()

# 4. FİRMAYA ÖZEL FİYAT TABLOSU
class FiyatTablosu(models.Model):
    firma = models.OneToOneField(Firma, on_delete=models.CASCADE, related_name="fiyat_tablosu", verbose_name="Firma")
    fiyatlar = models.JSONField(default=dict, help_text="Firmanın React tarafındaki fiyat JSON verisi")
    guncellenme_tarihi = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Fiyat Tablosu"
        verbose_name_plural = "4. Firma Fiyat Tabloları"

    def __str__(self):
        return f"{self.firma.ad} Fiyatları"

# 5. PROJE VE SEPET KALEMLERİ
class Proje(models.Model):
    DURUM_SECIMLERI = [
        ('teklif', '📝 Teklif Verildi / Onay Bekliyor'),
        ('kapora', '💵 Kapora / Ödeme Alındı'),
        ('olcu', '📐 Ölçü Bekleniyor / Kontrol Edilecek'),
        ('uretim', '🏭 Atölyede / İmalatta'),
        ('montaj', '🚛 Montaja Hazır / Sevkiyatta'),
        ('teslim', '✅ Montaj Tamamlandı & Teslim Edildi'),
    ]

    kullanici = models.ForeignKey(User, on_delete=models.CASCADE, related_name="projeler")
    proje_adi = models.CharField(max_length=255)
    musteri_tel = models.CharField(max_length=20, blank=True, null=True)
    teklif_tarihi = models.CharField(max_length=50)
    toplam_fiyat = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    durum = models.CharField(max_length=20, choices=DURUM_SECIMLERI, default='teklif')
    iban_bilgisi = models.CharField(max_length=100, blank=True, null=True, help_text="Fatura için kurumsal IBAN")
    notlar = models.TextField(blank=True, null=True, help_text="Müşteriye özel veya siparişe özel notlar")
    
    olusturulma_tarihi = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Proje (Sipariş)"
        verbose_name_plural = "5. Projeler ve Siparişler"

    def __str__(self):
        return f"{self.proje_adi} - {self.get_durum_display()}"

class SepetKalemi(models.Model):
    proje = models.ForeignKey(Proje, on_delete=models.CASCADE, related_name="kalemler")
    isim = models.CharField(max_length=255)
    urun_tipi = models.CharField(max_length=100)
    genislik = models.IntegerField()
    yukseklik = models.IntegerField()
    fiyat = models.DecimalField(max_digits=10, decimal_places=2)
    detaylar = models.JSONField(help_text="Renk, profil serisi, bölme ölçüleri vb.")

    def __str__(self):
        return self.isim

# 6. GOOGLE PLAY ZORUNLULUĞU: WEB ÜZERİNDEN HESAP SİLME TALEBİ
class HesapSilmeTalebi(models.Model):
    email = models.EmailField(verbose_name="E-posta Adresi")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Talep Tarihi")
    islendi_mi = models.BooleanField(default=False, verbose_name="İşlendi Mi?")

    class Meta:
        verbose_name = "Hesap Silme Talebi"
        verbose_name_plural = "6. Hesap Silme Talepleri"

    def __str__(self):
        return f"{self.email} ({'İşlendi' if self.islendi_mi else 'Bekliyor'})"