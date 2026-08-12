from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Firma, AbonelikPaketi, Proje, SepetKalemi

User = get_user_model()

# ==============================================================
# 🚀 KULLANICI KAYIT SERIALIZER (İÇERİ AKTARMA & FİRMA BAĞLANTISI)
# ==============================================================
class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    firma_adi = serializers.CharField(write_only=True, required=False, allow_blank=True)
    ad_soyad = serializers.CharField(write_only=True, required=False, allow_blank=True)
    paket_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'ad_soyad', 'telefon', 'firma_adi', 'paket_id']

    def create(self, validated_data):
        firma_adi = validated_data.pop('firma_adi', None)
        ad_soyad = validated_data.pop('ad_soyad', '')
        paket_id = validated_data.pop('paket_id', None)
        password = validated_data.pop('password')
        telefon_no = validated_data.get('telefon', '')

        if ad_soyad and not validated_data.get('first_name'):
            parcalar = ad_soyad.strip().split(' ')
            validated_data['first_name'] = parcalar[0]
            validated_data['last_name'] = ' '.join(parcalar[1:]) if len(parcalar) > 1 else ''

        secilen_paket = None
        if paket_id:
            try:
                secilen_paket = AbonelikPaketi.objects.get(id=paket_id)
            except AbonelikPaketi.DoesNotExist:
                pass

        if secilen_paket is None:
            secilen_paket = AbonelikPaketi.objects.filter(ad='Bireysel').first()

        isletme_adi = firma_adi if (firma_adi and firma_adi.strip()) else f"{validated_data['username']} Atölyesi"

        yeni_firma = Firma.objects.create(
            ad=isletme_adi,
            paket=secilen_paket,
            telefon=telefon_no
        )

        user = User.objects.create_user(
            password=password,
            firma=yeni_firma,
            firma_sahibi_mi=True,
            rol='patron',
            **validated_data
        )
        return user


# ==============================================================
# GİRİŞ YAPMIŞ KULLANICI (users/me/) SERIALIZER
# ==============================================================
class CurrentUserSerializer(serializers.ModelSerializer):
    firma_adi = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'telefon', 'rol', 'firma_adi']

    def get_firma_adi(self, obj):
        return obj.firma.ad if getattr(obj, 'firma', None) else None


# ==============================================================
# ABONELİK PAKETLERİ SERIALIZER
# ==============================================================
class AbonelikPaketiSerializer(serializers.ModelSerializer):
    class Meta:
        model = AbonelikPaketi
        fields = ['id', 'ad', 'periyot', 'fiyat', 'sinirsiz_kullanici', 'max_kullanici']


# ==============================================================
# PATRONUN ELEMAN EKLEMESİ İÇİN SERIALIZER
# ==============================================================
class CalisanEkleSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'telefon']

    def create(self, validated_data):
        request = self.context.get('request')
        patron = request.user
        password = validated_data.pop('password')

        calisan = User.objects.create_user(
            password=password,
            firma=patron.firma,
            firma_sahibi_mi=False,
            rol='usta',
            **validated_data
        )
        return calisan


# ==============================================================
# PROJE VE SEPET KALEMLERİ (CRM & BULUT ARŞİV) SERIALIZER
# ==============================================================
class SepetKalemiSerializer(serializers.ModelSerializer):
    class Meta:
        model = SepetKalemi
        fields = ['isim', 'urun_tipi', 'genislik', 'yukseklik', 'fiyat', 'detaylar']


class ProjeKaydetSerializer(serializers.ModelSerializer):
    kalemler = SepetKalemiSerializer(many=True) 

    class Meta:
        model = Proje
        # 🎯 Eksik olan notlar, iban_bilgisi ve durum alanları buraya eklendi
        fields = ['id', 'proje_adi', 'musteri_tel', 'notlar', 'iban_bilgisi', 'durum', 'teklif_tarihi', 'toplam_fiyat', 'kalemler']
        extra_kwargs = {
            'kullanici': {'required': False}
        }

    def create(self, validated_data):
        kalemler_data = validated_data.pop('kalemler', [])
        request = self.context.get('request')
        
        # Kullanıcı doğrulaması (güvenli bağlama)
        if not (request and hasattr(request, 'user') and request.user.is_authenticated):
            raise serializers.ValidationError("Proje kaydetmek için giriş yapmalısınız.")
        user = request.user

        proje = Proje.objects.create(kullanici=user, **validated_data)

        for kalem_data in kalemler_data:
            SepetKalemi.objects.create(proje=proje, **kalem_data)

        return proje