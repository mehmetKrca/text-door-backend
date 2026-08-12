from django.db import migrations


def paketleri_olustur(apps, schema_editor):
    AbonelikPaketi = apps.get_model('users', 'AbonelikPaketi')

    AbonelikPaketi.objects.filter(ad__in=['Bireysel', 'Kurumsal', 'Kurumsal Plus']).delete()

    AbonelikPaketi.objects.get_or_create(
        ad='Bireysel',
        defaults={
            'periyot': 'Aylık',
            'fiyat': 250,
            'sinirsiz_kullanici': False,
            'max_kullanici': 1,
        },
    )

    AbonelikPaketi.objects.get_or_create(
        ad='Kurumsal',
        defaults={
            'periyot': 'Aylık',
            'fiyat': 500,
            'sinirsiz_kullanici': True,
            'max_kullanici': 1,
        },
    )


def paketleri_geri_al(apps, schema_editor):
    AbonelikPaketi = apps.get_model('users', 'AbonelikPaketi')
    AbonelikPaketi.objects.filter(ad__in=['Bireysel', 'Kurumsal']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_hesapsilmetalebi'),
    ]

    operations = [
        migrations.RunPython(paketleri_olustur, paketleri_geri_al),
    ]
